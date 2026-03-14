import os
import asyncio
import platform
import psutil
import datetime
from pathlib import Path
from collections import Counter
from nicegui import ui, run, app
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

# --- RAG バックエンド ---
class RAGBackend:
    def __init__(self):
        self.target_dir = r"E:\sample\json"
        self.lm_studio_url = "http://localhost:1234/v1"
        self.db_path = "faiss_index_code"
        self.vectorstore = None
        self.embeddings = OpenAIEmbeddings(
            base_url=self.lm_studio_url,
            api_key="lm-studio",
            check_embedding_ctx_length=False
        )
        self.stats = {
            "total_chunks": 0,
            "last_rebuild": "Never",
            "file_count": 0,
            "revision": "v1.2.0",
            "is_rebuilding": False
        }

    def load_db(self):
        if os.path.exists(self.db_path):
            try:
                self.vectorstore = FAISS.load_local(
                    self.db_path, self.embeddings, allow_dangerous_deserialization=True
                )
                self.stats["total_chunks"] = self.vectorstore.index.ntotal
                idx_file = Path(self.db_path) / "index.faiss"
                if idx_file.exists():
                    mtime = datetime.datetime.fromtimestamp(idx_file.stat().st_mtime)
                    self.stats["last_rebuild"] = mtime.strftime("%Y-%m-%d %H:%M:%S")
                return True, "ベクトルDBを読み込みました。"
            except Exception as e:
                return False, f"読み込み失敗: {str(e)}"
        return False, "DBが見つかりません。新規構築が必要です。"

    def rebuild_db(self, progress_callback=None):
        self.stats["is_rebuilding"] = True
        docs = []
        code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            separators=["\nclass ", "\ndef ", "\nnamespace ", "\nvoid ", "\n\n", "\n", " ", ""]
        )

        extensions = {".hpp", ".h", ".cpp", ".py", ".json", ".js", ".ts", ".cs", ".java"}
        try:
            root_path = Path(self.target_dir)
            if not root_path.exists():
                return False, "ディレクトリが見つかりません。"

            files = [p for p in root_path.rglob('*') if p.suffix in extensions
                     and not any(part.startswith('.') or part in {".venv", "node_modules", "__pycache__", ".git"} for part in p.parts)]

            if not files:
                self.stats["is_rebuilding"] = False
                return False, "対象ファイルが見つかりません。"

            for i, p in enumerate(files):
                if progress_callback: progress_callback(f"Scanning: {i+1}/{len(files)}")
                try:
                    loader = TextLoader(str(p), encoding="utf-8")
                    raw_docs = loader.load()
                    for d in raw_docs:
                        d.metadata["source"] = str(p.relative_to(root_path))
                    docs.extend(code_splitter.split_documents(raw_docs))
                except: continue

            if progress_callback: progress_callback("Indexing...")
            self.vectorstore = FAISS.from_documents(docs, self.embeddings)
            self.vectorstore.save_local(self.db_path)

            self.stats["total_chunks"] = len(docs)
            self.stats["last_rebuild"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.stats["is_rebuilding"] = False
            return True, f"{len(docs)} チャンクでDBを更新しました。"
        except Exception as e:
            self.stats["is_rebuilding"] = False
            return False, f"エラー: {str(e)}"

    def get_retriever(self):
        return self.vectorstore.as_retriever(search_kwargs={"k": 8}) if self.vectorstore else None

    def get_file_content(self, rel_path):
        full_path = Path(self.target_dir) / rel_path
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return f"```{full_path.suffix.lstrip('.')}\n{content}\n```"
        except Exception as e: return f"Error: {str(e)}"

# --- UI ---
backend = RAGBackend()
USER_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'
AI_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>'

@ui.page('/')
async def main_page():
    ui.add_head_html('<style>body { background-color: #f8fafc; } .chat-bubble { border-radius: 1.25rem; } .status-item { display: flex; justify-content: space-between; margin-bottom: 12px; } .status-label { font-size: 10px; color: #94a3b8; font-weight: 800; } .status-value { font-size: 12px; color: #f1f5f9; } .rebuild-active { animation: pulse 1.5s infinite; color: #fbbf24 !important; } @keyframes pulse { 50% { opacity: 0.5; } }</style>')
    state = {'processing': False, 'hit_counts': Counter()}

    with ui.dialog().props('full-width') as preview_dialog, ui.card().classes('w-full max-h-[90vh] p-0 overflow-hidden'):
        with ui.row().classes('w-full items-center justify-between p-4 border-b'):
            preview_title = ui.label('').classes('font-bold')
            ui.button(icon='close', on_click=preview_dialog.close).props('flat round')
        with ui.scroll_area().classes('flex-grow p-6 bg-slate-900'):
            preview_content = ui.markdown('').classes('text-slate-100 font-mono')

    def open_preview(rel_path):
        preview_title.set_text(rel_path)
        preview_content.set_content(backend.get_file_content(rel_path))
        preview_dialog.open()

    with ui.left_drawer(value=True).classes('bg-slate-950 text-white p-0') as drawer:
        with ui.tabs().classes('w-full bg-slate-900 text-slate-400') as tabs:
            tab_explorer = ui.tab('Explorer', icon='folder')
            tab_settings = ui.tab('Settings', icon='settings')
            tab_status = ui.tab('Status', icon='analytics')

        with ui.tab_panels(tabs, value=tab_explorer).classes('w-full flex-grow bg-transparent p-0'):
            # Explorer
            with ui.tab_panel(tab_explorer).classes('p-0'):
                tree_container = ui.column().classes('w-full gap-0 p-2')
                def refresh_tree():
                    tree_container.clear()
                    root = Path(backend.target_dir)
                    if not root.exists():
                        with tree_container: ui.label('Invalid Path').classes('text-red-400 p-4')
                        return
                    def render(path, level=0):
                        rel = str(path.relative_to(root))
                        if any(x in rel for x in ['.venv', '.git', '__pycache__']): return
                        hits = state['hit_counts'].get(rel, 0)
                        with tree_container:
                            row = ui.row().classes('w-full items-center py-1 px-4 cursor-pointer hover:bg-slate-800').style(f'padding-left: {level*12+16}px; {"background:rgba(99,102,241,0.2)" if hits > 0 else ""}')
                            if not path.is_dir(): row.on('click', lambda: open_preview(rel))
                            with row:
                                ui.icon('folder' if path.is_dir() else 'description', size='16px').classes('text-slate-500 mr-2')
                                ui.label(f"{path.name} {'• '+str(hits) if hits > 0 else ''}").classes('text-xs text-slate-300')
                        if path.is_dir():
                            for c in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())): render(c, level+1)
                    render(root)

            # Settings
            with ui.tab_panel(tab_settings).classes('p-6'):
                ui.label('PROJECT SETTINGS').classes('text-[10px] font-bold text-slate-500 mb-4')
                # パス変更入力
                path_input = ui.input('Target Directory', value=backend.target_dir, on_change=lambda e: update_path(e.value)).props('dark outlined dens').classes('mb-4')

                rebuild_btn = ui.button('インデックス再構築', on_click=lambda: rebuild_db_task()).props('flat icon=bolt color=amber').classes('w-full border border-amber-900/30 mb-4 bg-amber-950/20')
                ui.button('DB再読み込み', on_click=lambda: load_db_task()).props('flat icon=refresh').classes('w-full border border-slate-800 mb-2')
                ui.button('終了', on_click=lambda: app.shutdown()).props('flat icon=power color=red').classes('w-full border border-red-900/30 mt-8')

            # Status
            with ui.tab_panel(tab_status).classes('p-6'):
                ui.label('SYSTEM').classes('text-[10px] font-bold text-indigo-400 mb-4')
                with ui.element('div').classes('status-item'):
                    ui.label('Vector DB').classes('status-label')
                    status_chip = ui.label('OFFLINE').classes('px-2 py-0.5 rounded text-[10px] font-bold')
                with ui.element('div').classes('status-item'):
                    ui.label('Chunks').classes('status-label')
                    chunk_count_label = ui.label('0').classes('status-value')
                with ui.element('div').classes('status-item'):
                    ui.label('CPU').classes('status-label')
                    cpu_label = ui.label('0%').classes('status-value')
                with ui.element('div').classes('status-item'):
                    ui.label('RAM').classes('status-label')
                    ram_label = ui.label('0GB').classes('status-value')

    def update_path(new_path):
        backend.target_dir = new_path
        refresh_tree()
        ui.notify(f"Target changed to: {new_path}")

    # --- Header & Chat ---
    with ui.header().classes('bg-white/80 backdrop-blur-md text-slate-800 p-4 border-b flex justify-between'):
        ui.label('CodeSentinel').classes('text-xl font-black text-indigo-600')
        ui.icon('circle', size='10px').classes('text-green-500 animate-pulse')

    chat_results = ui.column().classes('w-full max-w-4xl mx-auto p-6 pb-48 gap-8')
    with ui.footer().classes('bg-transparent'):
        with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
            with ui.row().classes('w-full bg-white p-3 border rounded-2xl shadow-2xl items-end gap-2'):
                input_field = ui.textarea(placeholder='質問を入力...').classes('flex-grow px-3').props('borderless autogrow')
                send_btn = ui.button(icon='send', on_click=lambda: handle_query()).props('round color=indigo shadow-lg')

    async def handle_query():
        if state['processing'] or not input_field.value.strip(): return
        query = input_field.value.strip(); input_field.value = ''; state['processing'] = True
        with chat_results:
            with ui.row().classes('w-full justify-end items-start gap-3'):
                ui.label(query).classes('bg-indigo-600 text-white p-4 chat-bubble max-w-[80%] shadow-lg')
            with ui.row().classes('w-full justify-start items-start gap-3'):
                with ui.element('div').classes('text-white bg-slate-900 p-2.5 rounded-2xl shadow-md mt-1'): ui.html(AI_ICON)
                with ui.column().classes('max-w-[85%]'):
                    response_card = ui.card().classes('p-6 rounded-3xl rounded-tl-none shadow-sm border w-full bg-white')
                    with response_card: md_output = ui.markdown('').classes('text-slate-800')
                    source_container = ui.row().classes('mt-2 gap-2')

        try:
            retriever = backend.get_retriever()
            if not retriever: md_output.set_content("DBを構築してください。")
            else:
                docs = await run.io_bound(retriever.invoke, query)
                state['hit_counts'] = Counter([d.metadata.get('source', '') for d in docs])
                refresh_tree()
                with source_container:
                    for src in list(dict.fromkeys([d.metadata.get('source', '') for d in docs])):
                        ui.button(src, on_click=lambda s=src: open_preview(s)).props('flat no-caps dense').classes('text-[10px] bg-slate-50 text-indigo-600 rounded-lg px-2 border')

                llm = ChatOpenAI(base_url=backend.lm_studio_url, api_key="lm-studio", temperature=0.1, streaming=True)
                prompt = ChatPromptTemplate.from_template("回答は日本語で。\nコンテキスト: {context}\n質問: {input}")
                full_content = ""
                async for chunk in (prompt | llm | StrOutputParser()).astream({"context": "\n".join([d.page_content for d in docs]), "input": query}):
                    full_content += chunk
                    md_output.set_content(full_content)
                    ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')
        except Exception as e: md_output.set_content(f"Error: {e}")
        finally: state['processing'] = False

    def load_db_task():
        success, msg = backend.load_db()
        # 1. テキストをセットする
        status_chip.set_text('ONLINE' if success else 'OFFLINE')

        # 2. クラス（色）をセットする (2行に分ける)
        new_classes = 'bg-green-950/20 text-green-400' if success else 'bg-red-950/20 text-red-400'
        status_chip.classes(replace=new_classes)

        chunk_count_label.set_text(str(backend.stats["total_chunks"]))
        if success:
            refresh_tree()
        ui.notify(msg)

    async def rebuild_db_task():
        n = ui.notification('Indexing...', spinner=True, infinite=True)
        rebuild_btn.disable()
        success, msg = await run.io_bound(backend.rebuild_db, progress_callback=lambda t: chunk_count_label.set_text(t))
        n.dismiss(); rebuild_btn.enable()
        load_db_task()

    ui.timer(2.0, lambda: (cpu_label.set_text(f"{psutil.cpu_percent()}%"), ram_label.set_text(f"{psutil.virtual_memory().used//1024**3}GB")))
    ui.timer(0.1, load_db_task, once=True)

ui.run(title='CodeSentinel', port=8080, reload=False)
