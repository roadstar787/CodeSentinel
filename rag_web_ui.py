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
            "revision": "v1.1.4",
            "is_rebuilding": False
        }

    def load_db(self):
        if os.path.exists(self.db_path):
            try:
                self.vectorstore = FAISS.load_local(
                    self.db_path, self.embeddings, allow_dangerous_deserialization=True
                )
                self.stats["total_chunks"] = self.vectorstore.index.ntotal
                return True, "ベクトルDBを読み込みました。"
            except Exception as e:
                return False, f"読み込み失敗: {str(e)}"
        return False, "DBが見つかりません。新規作成が必要です。"

    def rebuild_db(self, progress_callback=None):
        """最適化されたチャンク設定でDBを再構築する（進捗フィードバック付き）"""
        self.stats["is_rebuilding"] = True
        docs = []
        code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            separators=["\nclass ", "\ndef ", "\nvoid ", "\nint ", "\nstatic ", "\n\n", "\n", " ", ""]
        )

        extensions = {".hpp", ".h", ".cpp", ".py", ".json"}
        try:
            files = [p for p in Path(self.target_dir).rglob('*') if p.suffix in extensions and ".venv" not in p.parts and ".git" not in p.parts]
            total_files = len(files)

            if not files:
                self.stats["is_rebuilding"] = False
                return False, "対象ファイルが見つかりませんでした。"

            for i, p in enumerate(files):
                if progress_callback:
                    progress_callback(f"Scanning: {i+1}/{total_files}")

                loader = TextLoader(str(p), encoding="utf-8")
                raw_docs = loader.load()
                for d in raw_docs:
                    d.metadata["source"] = str(p.relative_to(self.target_dir))
                docs.extend(code_splitter.split_documents(raw_docs))

            if progress_callback: progress_callback("Indexing...")
            self.vectorstore = FAISS.from_documents(docs, self.embeddings)

            if progress_callback: progress_callback("Finalizing...")
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
        return self.vectorstore.as_retriever(search_kwargs={"k": 10})

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

@app.on_shutdown
def cleanup():
    backend.vectorstore = None

@ui.page('/')
async def main_page():
    ui.add_head_html('''
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono&family=Noto+Sans+JP:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --font-sans: "Inter", "Noto Sans JP", sans-serif;
                --font-mono: "JetBrains Mono", monospace;
            }
            body { font-family: var(--font-sans); background-color: #f8fafc; }
            .custom-scrollbar .q-scrollarea__thumb { background: #475569 !important; opacity: 0.7 !important; border-radius: 4px; }
            .no-padding-panel .q-tab-panel { padding: 0 !important; }
            .multi-line-input textarea { font-family: var(--font-sans); line-height: 1.6 !important; max-height: 200px; font-size: 15px; }
            .code-preview pre, .code-preview code { font-family: var(--font-mono) !important; font-size: 13px !important; }
            .chat-bubble { font-size: 0.95rem; line-height: 1.7; border-radius: 1.25rem; }
            .status-item { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; width: 100%; }
            .status-label { font-size: 10px; color: #94a3b8; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; }
            .status-value { font-size: 12px; color: #f1f5f9; font-family: var(--font-mono); font-weight: 500; }

            @keyframes pulse-sync {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.7; transform: scale(0.97); }
            }
            .rebuild-active {
                animation: pulse-sync 1.5s ease-in-out infinite;
                color: #fbbf24 !important;
                border-color: #fbbf24 !important;
                pointer-events: none; /* 連打防止 */
            }
            .rebuild-active-btn {
                background: rgba(251, 191, 36, 0.2) !important;
            }
        </style>
    ''')

    state = {'processing': False, 'hit_counts': Counter()}

    # --- ダイアログ ---
    with ui.dialog().props('full-width') as preview_dialog, ui.card().classes('w-full max-h-[90vh] flex flex-col p-0 overflow-hidden'):
        with ui.row().classes('w-full items-center justify-between p-4 border-b bg-white'):
            preview_title = ui.label('').classes('font-bold text-slate-800')
            ui.button(icon='close', on_click=preview_dialog.close).props('flat round text-color=slate-400')
        with ui.scroll_area().classes('flex-grow p-6 bg-slate-900 code-preview'):
            preview_content = ui.markdown('').classes('text-slate-100')

    def open_preview(rel_path):
        preview_title.set_text(f"File: {rel_path}")
        preview_content.set_content(backend.get_file_content(rel_path))
        preview_dialog.open()

    # --- サイドバー ---
    with ui.left_drawer(value=True).classes('bg-slate-950 text-white p-0 shadow-2xl flex flex-col no-padding-panel') as drawer:
        with ui.tabs().classes('w-full bg-slate-900 text-slate-400 border-b border-slate-800') as tabs:
            tab_explorer = ui.tab('Explorer', icon='folder')
            tab_settings = ui.tab('Settings', icon='settings')
            tab_status = ui.tab('Status', icon='analytics')

        with ui.tab_panels(tabs, value=tab_explorer).classes('w-full flex-grow bg-transparent text-white p-0'):
            # Explorer
            with ui.tab_panel(tab_explorer).classes('flex flex-col h-full'):
                with ui.column().classes('w-full px-5 py-4 border-b border-slate-900'):
                    ui.label('FILE NAVIGATOR').classes('text-[10px] font-black text-slate-500 tracking-[0.2em]')
                with ui.scroll_area().classes('flex-grow px-0 custom-scrollbar') as tree_scroll:
                    tree_container = ui.column().classes('gap-0')

                def refresh_tree():
                    tree_container.clear()
                    hit_data = state['hit_counts']
                    root = Path(backend.target_dir)
                    if not root.exists(): return
                    def render_node(path, level=0):
                        rel_p = str(path.relative_to(root))
                        if any(x in rel_p for x in ['.venv', '__pycache__', '.git']): return
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
                    .props('flat icon=bolt color=amber').classes('w-full border border-amber-900/30 mb-4 rounded-xl py-3 bg-amber-950/20 font-bold transition-all')

                ui.button('DB再読み込み', on_click=lambda: load_db_task()).props('flat icon=refresh').classes('text-white w-full border border-slate-800 mb-2 rounded-xl py-2')
                ui.button('終了', on_click=lambda: app.shutdown()).props('flat icon=power_settings_new color=red').classes('w-full border border-red-900/30 rounded-xl py-2 mt-12 bg-red-950/20')

            # Status
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
                    chunk_count_label = ui.label('0').classes('status-value transition-all')
                with ui.element('div').classes('status-item'):
                    ui.label('Last Build').classes('status-label')
                    last_update_label = ui.label('Never').classes('status-value')

                ui.separator().classes('bg-slate-800 my-6')
                ui.label('SYSTEM LOAD').classes('text-[10px] font-bold text-indigo-400 mb-4 tracking-widest')
                with ui.element('div').classes('status-item'):
                    ui.label('CPU').classes('status-label')
                    cpu_label = ui.label('0%').classes('status-value')
                with ui.element('div').classes('status-item'):
                    ui.label('RAM').classes('status-label')
                    ram_label = ui.label('0GB').classes('status-value')

                async def update_system_stats():
                    cpu_label.set_text(f"{psutil.cpu_percent()}%")
                    mem = psutil.virtual_memory()
                    ram_label.set_text(f"{mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB")
                ui.timer(2.0, update_system_stats)

    # --- Header ---
    with ui.header().classes('bg-white/80 backdrop-blur-md text-slate-800 p-4 border-b flex items-center justify-between shadow-sm'):
        with ui.row().classes('items-center gap-3'):
            ui.button(on_click=lambda: drawer.toggle()).props('flat round icon=menu').classes('text-slate-400')
            ui.label('CodeRAG').classes('text-xl font-black tracking-tighter text-indigo-600')
            ui.badge('v1.1').props('color=indigo-1 text-color=indigo-600 shadow-none').classes('rounded-md px-2 py-0.5 text-[10px] font-bold')

        with ui.row().classes('items-center gap-2'):
            ui.icon('circle', size='10px').classes('text-green-500 animate-pulse')
            ui.label('LM Studio Linked').classes('text-[11px] font-bold text-slate-400')

    # --- Chat Display ---
    chat_results = ui.column().classes('w-full max-w-4xl mx-auto p-6 pb-48 gap-8')

    # --- Footer Input ---
    with ui.footer().classes('bg-transparent p-0'):
        with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
            with ui.row().classes('w-full bg-white p-3 border border-slate-200 rounded-2xl shadow-2xl items-end gap-2'):
                input_field = ui.textarea(placeholder='Ask a question about your project...').classes('flex-grow px-3 multi-line-input').props('borderless autogrow')
                ui.button(icon='send', on_click=lambda: handle_query()).props('round color=indigo shadow-lg').classes('mb-1 hover:scale-105 transition-transform')

    async def handle_query():
        if state['processing'] or not input_field.value.strip(): return
        query = input_field.value.strip(); input_field.value = ''; state['processing'] = True

        # ユーザーの入力を表示
        with chat_results:
            with ui.row().classes('w-full justify-end items-start gap-3'):
                ui.label(query).classes('bg-indigo-600 text-white p-4 chat-bubble max-w-[80%] shadow-lg shadow-indigo-100 font-medium')
                with ui.element('div').classes('text-indigo-600 bg-indigo-50 p-2.5 rounded-2xl shadow-sm mt-1'):
                    ui.html(USER_ICON)

        # AI側の回答領域を準備
        with chat_results:
            with ui.row().classes('w-full justify-start items-start gap-3'):
                with ui.element('div').classes('text-white bg-slate-900 p-2.5 rounded-2xl shadow-md mt-1'):
                    ui.html(AI_ICON)
                with ui.column().classes('max-w-[85%]'):
                    response_card = ui.card().classes('p-6 rounded-3xl rounded-tl-none shadow-sm border border-slate-100 w-full bg-white')
                    with response_card: md_output = ui.markdown('').classes('text-slate-800 leading-relaxed')
                    source_container = ui.row().classes('mt-2 gap-2 flex-wrap items-center')

        # インデックス構築中のチェック
        if backend.stats["is_rebuilding"]:
            md_output.set_content("現在インデックスを再構築中です。完了するまでしばらくお待ちください...")
            state['processing'] = False
            return

        try:
            retriever = backend.get_retriever()
            if not retriever:
                md_output.set_content("データベースが初期化されていません。Settingsからインデックスを再構築してください。")
                return

            docs = await run.io_bound(retriever.invoke, query)
            state['hit_counts'] = Counter([d.metadata.get('source', '') for d in docs])
            refresh_tree()

            with source_container:
                for src in list(set([d.metadata.get('source', '') for d in docs])):
                    ui.button(src, on_click=lambda s=src: open_preview(s)).props('flat no-caps dense').classes('text-[10px] bg-slate-50 text-indigo-600 rounded-lg px-2 border border-indigo-50 hover:bg-indigo-50 font-mono')

            context_text = "\n\n".join([f"Source: {d.metadata.get('source')}\n{d.page_content}" for d in docs])
            llm = ChatOpenAI(base_url=backend.lm_studio_url, api_key="lm-studio", temperature=0.1, streaming=True)
            prompt = ChatPromptTemplate.from_template("回答は日本語で行ってください。\n\nコンテキスト: {context}\n質問: {input}")
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

    def load_db_task():
        success, msg = backend.load_db()
        status_chip.set_text('ONLINE' if success else 'OFFLINE')
        status_chip.classes(replace='bg-green-950/20 text-green-400' if success else 'bg-red-950/20 text-red-400')
        chunk_count_label.set_text(str(backend.stats["total_chunks"]))
        last_update_label.set_text(backend.stats["last_rebuild"])
        ui.notify(msg, color='positive' if success else 'negative', position='top-right')
        refresh_tree()

    async def rebuild_db_task():
        if backend.stats["is_rebuilding"]: return

        n = ui.notification('Initializing Rebuild...', spinner=True, infinite=True)

        # ボタンとラベルにアニメーションを適用 & テキスト変更
        chunk_count_label.classes(add='rebuild-active')
        rebuild_btn.classes(add='rebuild-active rebuild-active-btn')
        rebuild_btn.set_text('再構築中...')

        def update_progress(text):
            chunk_count_label.set_text(text)

        success, msg = await run.io_bound(backend.rebuild_db, progress_callback=update_progress)

        n.dismiss()
        # アニメーション解除 & テキスト復元
        chunk_count_label.classes(remove='rebuild-active')
        rebuild_btn.classes(remove='rebuild-active rebuild-active-btn')
        rebuild_btn.set_text('インデックス再構築')

        ui.notify(msg, color='positive' if success else 'negative', position='top-right')
        load_db_task()

    load_db_task()

ui.run(title='CodeRAG Explorer', port=8080, reload=False, show=True)
