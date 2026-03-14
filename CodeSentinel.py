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
            "revision": "v1.1.5",
            "is_rebuilding": False
        }

    def load_db(self):
        """DBのロードと最終更新日時の同期"""
        if os.path.exists(self.db_path):
            try:
                # 依存関係の最新仕様に合わせ、embeddingsを明示的に渡す
                self.vectorstore = FAISS.load_local(
                    self.db_path, self.embeddings, allow_dangerous_deserialization=True
                )
                self.stats["total_chunks"] = self.vectorstore.index.ntotal

                # インデックスファイルの更新日時を反映
                idx_file = Path(self.db_path) / "index.faiss"
                if idx_file.exists():
                    mtime = datetime.datetime.fromtimestamp(idx_file.stat().st_mtime)
                    self.stats["last_rebuild"] = mtime.strftime("%Y-%m-%d %H:%M:%S")

                return True, "ベクトルDBを読み込みました。"
            except Exception as e:
                return False, f"読み込み失敗: {str(e)}"
        return False, "DBが見つかりません。新規作成が必要です。"

    def rebuild_db(self, progress_callback=None):
        """最適化されたチャンク設定でDBを再構築"""
        self.stats["is_rebuilding"] = True
        docs = []
        # コード解析に適したセパレーターを追加
        code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            separators=["\nclass ", "\ndef ", "\nnamespace ", "\nvoid ", "\nint ", "\nstatic ", "\n\n", "\n", " ", ""]
        )

        extensions = {".hpp", ".h", ".cpp", ".py", ".json", ".js", ".ts"}
        try:
            root_path = Path(self.target_dir)
            if not root_path.exists():
                return False, f"ターゲットディレクトリが存在しません: {self.target_dir}"

            files = [p for p in root_path.rglob('*') if p.suffix in extensions and not any(part.startswith('.') or part in {".venv", "node_modules", "__pycache__"} for part in p.parts)]
            total_files = len(files)

            if not files:
                self.stats["is_rebuilding"] = False
                return False, "対象ファイルが見つかりませんでした。"

            for i, p in enumerate(files):
                if progress_callback:
                    progress_callback(f"Scanning: {i+1}/{total_files}")
                try:
                    loader = TextLoader(str(p), encoding="utf-8")
                    raw_docs = loader.load()
                    for d in raw_docs:
                        d.metadata["source"] = str(p.relative_to(root_path))
                    docs.extend(code_splitter.split_documents(raw_docs))
                except Exception:
                    continue # 読み取り不可ファイルはスキップ

            if progress_callback: progress_callback("Indexing...")
            self.vectorstore = FAISS.from_documents(docs, self.embeddings)

            if progress_callback: progress_callback("Saving...")
            self.vectorstore.save_local(self.db_path)

            self.stats["total_chunks"] = len(docs)
            self.stats["file_count"] = len(files)
            self.stats["last_rebuild"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.stats["is_rebuilding"] = False
            return True, f"{len(docs)} チャンクでDBを再構築しました。"
        except Exception as e:
            self.stats["is_rebuilding"] = False
            return False, f"再構築エラー: {str(e)}"

    def get_retriever(self):
        if not self.vectorstore: return None
        return self.vectorstore.as_retriever(search_kwargs={"k": 8})

    def get_file_content(self, rel_path):
        full_path = Path(self.target_dir) / rel_path
        if not full_path.exists() or full_path.is_dir(): return "ファイルが見つかりません。"
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            ext = full_path.suffix.lstrip('.')
            return f"```{ext}\n{content}\n```"
        except Exception as e:
            return f"読み込みエラー: {str(e)}"

# --- UI コンポーネント ---
backend = RAGBackend()

USER_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'
AI_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>'

@ui.page('/')
async def main_page():
    ui.add_head_html('''
        <style>
            :root {
                --font-sans: "Inter", "Noto Sans JP", sans-serif;
                --font-mono: "JetBrains Mono", monospace;
            }
            body { font-family: var(--font-sans); background-color: #f8fafc; }
            .chat-bubble { font-size: 0.95rem; line-height: 1.7; border-radius: 1.25rem; }
            .status-item { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; width: 100%; }
            .status-label { font-size: 10px; color: #94a3b8; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; }
            .status-value { font-size: 12px; color: #f1f5f9; font-family: var(--font-mono); }
            @keyframes pulse-sync {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.7; transform: scale(0.97); }
            }
            .rebuild-active { animation: pulse-sync 1.5s ease-in-out infinite; color: #fbbf24 !important; }
        </style>
    ''')

    state = {'processing': False, 'hit_counts': Counter()}

    # --- ダイアログ ---
    with ui.dialog().props('full-width') as preview_dialog, ui.card().classes('w-full max-h-[90vh] flex flex-col p-0 overflow-hidden'):
        with ui.row().classes('w-full items-center justify-between p-4 border-b bg-white'):
            preview_title = ui.label('').classes('font-bold text-slate-800')
            ui.button(icon='close', on_click=preview_dialog.close).props('flat round text-color=slate-400')
        with ui.scroll_area().classes('flex-grow p-6 bg-slate-900'):
            preview_content = ui.markdown('').classes('text-slate-100 font-mono')

    def open_preview(rel_path):
        preview_title.set_text(f"File: {rel_path}")
        preview_content.set_content(backend.get_file_content(rel_path))
        preview_dialog.open()

    # --- サイドバー ---
    with ui.left_drawer(value=True).classes('bg-slate-950 text-white p-0 shadow-2xl flex flex-col') as drawer:
        with ui.tabs().classes('w-full bg-slate-900 text-slate-400 border-b border-slate-800') as tabs:
            tab_explorer = ui.tab('Explorer', icon='folder')
            tab_settings = ui.tab('Settings', icon='settings')
            tab_status = ui.tab('Status', icon='analytics')

        with ui.tab_panels(tabs, value=tab_explorer).classes('w-full flex-grow bg-transparent text-white p-0'):
            # Explorer
            with ui.tab_panel(tab_explorer).classes('flex flex-col h-full'):
                with ui.column().classes('w-full px-5 py-4 border-b border-slate-900'):
                    ui.label('FILE NAVIGATOR').classes('text-[10px] font-black text-slate-500 tracking-[0.2em]')
                with ui.scroll_area().classes('flex-grow px-0') as tree_scroll:
                    tree_container = ui.column().classes('gap-0')

                def refresh_tree():
                    tree_container.clear()
                    hit_data = state['hit_counts']
                    root = Path(backend.target_dir)
                    if not root.exists():
                        with tree_container: ui.label('Directory not found').classes('px-5 text-red-400 text-xs')
                        return

                    def render_node(path, level=0):
                        rel_p = str(path.relative_to(root))
                        if any(x in rel_p for x in ['.venv', '__pycache__', '.git', 'node_modules']): return

                        hits = hit_data.get(rel_p, 0)
                        bg_style = f'background: rgba(99, 102, 241, {min(hits * 0.15, 0.4)});' if hits > 0 else ''

                        with tree_container:
                            row = ui.row().classes('w-full items-center no-wrap py-1.5 px-5 cursor-pointer hover:bg-slate-800/50 transition-all').style(f'padding-left: {level * 12 + 20}px; {bg_style}')
                            if not path.is_dir(): row.on('click', lambda p=rel_p: open_preview(p))
                            with row:
                                ui.icon('folder' if path.is_dir() else 'description', size='16px').classes('text-slate-600 mr-2 flex-shrink-0')
                                ui.label(f"{path.name}" + (f" • {hits}" if hits > 0 else "")).classes('text-[12px] whitespace-nowrap text-slate-400')

                        if path.is_dir():
                            try:
                                for child in sorted(list(path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower())):
                                    render_node(child, level + 1)
                            except: pass
                    render_node(root)

            # Settings
            with ui.tab_panel(tab_settings).classes('p-6'):
                ui.label('KNOWLEDGE MANAGEMENT').classes('text-[10px] font-bold text-slate-500 mb-4 tracking-widest')
                rebuild_btn = ui.button('インデックス再構築', on_click=lambda: rebuild_db_task())\
                    .props('flat icon=bolt color=amber').classes('w-full border border-amber-900/30 mb-4 rounded-xl py-3 bg-amber-950/20 font-bold')

                ui.button('DB再読み込み', on_click=lambda: load_db_task()).props('flat icon=refresh').classes('text-white w-full border border-slate-800 mb-2 rounded-xl py-2')
                ui.button('終了', on_click=lambda: app.shutdown()).props('flat icon=power_settings_new color=red').classes('w-full border border-red-900/30 rounded-xl py-2 mt-12 bg-red-950/20')

            # Status
            # --- Status タブ内の修正済みブロック ---
            with ui.tab_panel(tab_status).classes('p-6'):
                ui.label('SYSTEM STATUS').classes('text-[10px] font-bold text-indigo-400 mb-4 tracking-widest')

                with ui.element('div').classes('status-item'):
                    ui.label('Revision').classes('status-label')
                    ui.label(backend.stats["revision"]).classes('status-value text-indigo-400')

                with ui.element('div').classes('status-item'):
                    ui.label('Vector DB').classes('status-label')
                    status_chip = ui.label('OFFLINE').classes('px-2 py-0.5 rounded text-[10px] font-bold')

                with ui.element('div').classes('status-item'):
                    ui.label('Total Chunks').classes('status-label')
                    chunk_count_label = ui.label('0').classes('status-value')

                with ui.element('div').classes('status-item'):
                    ui.label('Last Build').classes('status-label')
                    last_update_label = ui.label('Never').classes('status-value')

                ui.separator().classes('bg-slate-800 my-6')

                with ui.element('div').classes('status-item'):
                    ui.label('CPU').classes('status-label')
                    cpu_label = ui.label('0%').classes('status-value')

                with ui.element('div').classes('status-item'):
                    ui.label('RAM').classes('status-label')
                    ram_label = ui.label('0GB').classes('status-value')


    # --- Header ---
    with ui.header().classes('bg-white/80 backdrop-blur-md text-slate-800 p-4 border-b flex items-center justify-between shadow-sm'):
        with ui.row().classes('items-center gap-3'):
            ui.button(on_click=lambda: drawer.toggle()).props('flat round icon=menu').classes('text-slate-400')
            ui.label('CodeSentinel').classes('text-xl font-black tracking-tighter text-indigo-600')

        with ui.row().classes('items-center gap-2'):
            ui.icon('circle', size='10px').classes('text-green-500 animate-pulse')
            ui.label('LM Studio Linked').classes('text-[11px] font-bold text-slate-400')

    chat_results = ui.column().classes('w-full max-w-4xl mx-auto p-6 pb-48 gap-8')

    # --- Footer Input ---
    with ui.footer().classes('bg-transparent p-0'):
        with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
            with ui.row().classes('w-full bg-white p-3 border border-slate-200 rounded-2xl shadow-2xl items-end gap-2'):
                input_field = ui.textarea(placeholder='プロジェクトについて質問する...').classes('flex-grow px-3').props('borderless autogrow')
                send_btn = ui.button(icon='send', on_click=lambda: handle_query()).props('round color=indigo shadow-lg').classes('mb-1')

    async def handle_query():
        if state['processing'] or not input_field.value.strip(): return
        query = input_field.value.strip(); input_field.value = ''; state['processing'] = True
        send_btn.disable()

        # ユーザー発言
        with chat_results:
            with ui.row().classes('w-full justify-end items-start gap-3'):
                ui.label(query).classes('bg-indigo-600 text-white p-4 chat-bubble max-w-[80%] shadow-lg shadow-indigo-100 font-medium')
                with ui.element('div').classes('text-indigo-600 bg-indigo-50 p-2.5 rounded-2xl shadow-sm mt-1'): ui.html(USER_ICON)

        # AI発言準備
        with chat_results:
            with ui.row().classes('w-full justify-start items-start gap-3'):
                with ui.element('div').classes('text-white bg-slate-900 p-2.5 rounded-2xl shadow-md mt-1'): ui.html(AI_ICON)
                with ui.column().classes('max-w-[85%]'):
                    response_card = ui.card().classes('p-6 rounded-3xl rounded-tl-none shadow-sm border border-slate-100 w-full bg-white')
                    with response_card: md_output = ui.markdown('').classes('text-slate-800 leading-relaxed')
                    source_container = ui.row().classes('mt-2 gap-2 flex-wrap items-center')

        if backend.stats["is_rebuilding"]:
            md_output.set_content("現在インデックス再構築中のため、応答できません。")
            state['processing'] = False
            send_btn.enable()
            return

        try:
            retriever = backend.get_retriever()
            if not retriever:
                md_output.set_content("DBが未初期化です。Settingsから構築してください。")
            else:
                docs = await run.io_bound(retriever.invoke, query)
                state['hit_counts'] = Counter([d.metadata.get('source', '') for d in docs])
                refresh_tree()

                with source_container:
                    for src in list(dict.fromkeys([d.metadata.get('source', '') for d in docs])):
                        ui.button(src, on_click=lambda s=src: open_preview(s)).props('flat no-caps dense').classes('text-[10px] bg-slate-50 text-indigo-600 rounded-lg px-2 border border-indigo-50 font-mono')

                context_text = "\n\n".join([f"Source: {d.metadata.get('source')}\n{d.page_content}" for d in docs])
                llm = ChatOpenAI(base_url=backend.lm_studio_url, api_key="lm-studio", temperature=0.1, streaming=True)
                prompt = ChatPromptTemplate.from_template("回答は日本語で行ってください。コードベースの情報を基に、簡潔かつ正確に答えてください。\n\nコンテキスト: {context}\n質問: {input}")
                chain = prompt | llm | StrOutputParser()

                full_content = ""
                async for chunk in chain.astream({"context": context_text, "input": query}):
                    full_content += chunk
                    md_output.set_content(full_content)
                    ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')
        except Exception as e:
            md_output.set_content(f"⚠️ **Error**: {str(e)}")
        finally:
            state['processing'] = False
            send_btn.enable()

    def load_db_task():
        success, msg = backend.load_db()
        status_chip.set_text('ONLINE' if success else 'OFFLINE')
        status_chip.classes(replace='bg-green-950/20 text-green-400' if success else 'bg-red-950/20 text-red-400')
        chunk_count_label.set_text(str(backend.stats["total_chunks"]))
        last_update_label.set_text(backend.stats["last_rebuild"])
        if success: refresh_tree()
        ui.notify(msg, color='positive' if success else 'negative', position='top-right')

    async def rebuild_db_task():
        if backend.stats["is_rebuilding"]: return
        n = ui.notification('Indexing project...', spinner=True, infinite=True)
        chunk_count_label.classes(add='rebuild-active')
        rebuild_btn.set_text('再構築中...'); rebuild_btn.disable()

        success, msg = await run.io_bound(backend.rebuild_db, progress_callback=lambda t: chunk_count_label.set_text(t))

        n.dismiss()
        chunk_count_label.classes(remove='rebuild-active')
        rebuild_btn.set_text('インデックス再構築'); rebuild_btn.enable()
        load_db_task()

    # 初期化
    ui.timer(0.1, load_db_task, once=True)

ui.run(title='CodeSentinel Explorer', port=8080, reload=False)
