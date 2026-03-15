import os
import sys
import asyncio
import psutil
import httpx
from pathlib import Path
from nicegui import ui, run, app
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

# --- システム設定 ---
APP_NAME = "Code Sentinel"
REVISION = "v1.3.3"

class RAGBackend:
    def __init__(self):
        self.target_dir = r"E:\sample\json"
        self.db_path = "faiss_index_code"
        self.lm_studio_url = "http://localhost:1234/v1"
        self.vectorstore = None
        self.embeddings = OpenAIEmbeddings(
            base_url=self.lm_studio_url,
            api_key="lm-studio",
            check_embedding_ctx_length=False
        )
        self.stats = {"total_chunks": 0, "is_rebuilding": False, "lm_connected": False, "model": "N/A"}

    async def check_lm_studio(self):
        try:
            async with httpx.AsyncClient() as client:
                # タイムアウトを少し伸ばす
                resp = await client.get(f"{self.lm_studio_url}/models", timeout=30.0)
                if resp.status_code == 200:
                    self.stats["lm_connected"] = True
                    data = resp.json()
                    if data.get('data'):
                        self.stats["model"] = data['data'][0]['id']
                    return True
                else:
                    print(f"LM Studio returned status: {resp.status_code}")
        except Exception as e:
            # 接続エラーの理由をターミナル（黒い画面）に表示
            print(f"Connection Error Detail: {e}")

        self.stats["lm_connected"] = False
        return False
    def load_db(self):
        if os.path.exists(self.db_path):
            try:
                self.vectorstore = FAISS.load_local(self.db_path, self.embeddings, allow_dangerous_deserialization=True)
                self.stats["total_chunks"] = self.vectorstore.index.ntotal
                return True
            except: return False
        return False

# --- 抜けていたメソッドを修正 ---
    def get_retriever(self):
        if self.vectorstore:
            return self.vectorstore.as_retriever(search_kwargs={"k": 5})
        return None
    
    def rebuild_db(self):
        self.stats["is_rebuilding"] = True
        docs = []
        extensions = {".hpp", ".h", ".cpp", ".py", ".json", ".cs"}
        try:
            path_obj = Path(self.target_dir)
            files = [p for p in path_obj.rglob('*') if p.suffix in extensions and ".venv" not in p.parts]
            for p in files:
                try:
                    loader = TextLoader(str(p), encoding="utf-8")
                    raw = loader.load()
                    for d in raw: d.metadata["source"] = str(p.relative_to(self.target_dir))
                    docs.extend(RecursiveCharacterTextSplitter(chunk_size=1000).split_documents(raw))
                except: continue
            self.vectorstore = FAISS.from_documents(docs, self.embeddings)
            self.vectorstore.save_local(self.db_path)
            self.stats["total_chunks"] = len(docs)
            return True, "SUCCESS"
        finally: self.stats["is_rebuilding"] = False

backend = RAGBackend()

@ui.page('/')
async def main_page():
    backend.target_dir = app.storage.user.get('target_dir', backend.target_dir)

    ui.add_head_html('''
        <style>
            .hit-file { color: #fbbf24 !important; font-weight: bold; background: #1e293b; border-radius: 4px; padding: 0 4px; }
            .rebuild-active { animation: pulse 1.5s infinite; color: #fbbf24 !important; }
            @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        </style>
    ''')

    # --- プレビューダイアログ ---
    with ui.dialog() as preview_dialog, ui.card().classes('w-[80vw] max-w-4xl h-[80vh]'):
        preview_title = ui.label('').classes('text-sm font-bold mb-2')
        with ui.scroll_area().classes('w-full flex-grow border p-4 bg-[#0d1117]'):
            preview_code = ui.markdown('').classes('text-xs text-slate-300')
        ui.button('CLOSE', on_click=preview_dialog.close).props('flat').classes('ml-auto')

    def open_preview(file_path):
        if not file_path: return
        full_path = Path(backend.target_dir) / file_path
        if not full_path.is_file(): return
        try:
            content = full_path.read_text(encoding='utf-8')
            preview_title.set_text(f"PREVIEW: {file_path}")
            # 言語指定付きでMarkdownセット
            ext = full_path.suffix[1:] or 'text'
            preview_code.set_content(f"```{ext}\n{content}\n```")
            preview_dialog.open()
        except Exception as e:
            ui.notify(f"Read Error: {e}", color='red')

    # --- サイドバー (復活) ---
    with ui.left_drawer(fixed=True).classes('p-0 bg-[#0a0f18]') as drawer:
        with ui.tabs().classes('w-full text-slate-500') as tabs:
            tab_exp = ui.tab('EXP', icon='account_tree')
            tab_set = ui.tab('SET', icon='settings')
            tab_sts = ui.tab('STS', icon='hub')

        with ui.tab_panels(tabs, value=tab_exp).classes('w-full bg-transparent p-4'):
            with ui.tab_panel(tab_exp):
                ui.label('EXPLORER').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
                tree_container = ui.column().classes('w-full gap-0')

            with ui.tab_panel(tab_set):
                ui.label('CONFIG').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
                path_input = ui.input('Path', value=backend.target_dir).props('dark dense outlined').classes('w-full mb-4')
                ui.button('SAVE PATH', on_click=lambda: save_settings(path_input.value)).props('flat border').classes('w-full text-xs mb-4')
                rebuild_btn = ui.button('REBUILD', on_click=lambda: rebuild_task()).props('flat icon=refresh').classes('w-full border border-slate-800 text-xs')

            with ui.tab_panel(tab_sts):
                ui.label('SYSTEM').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
                with ui.row().classes('items-center gap-2 mb-2'):
                    lm_indicator = ui.icon('circle', color='grey').classes('text-[12px]')
                    lm_status_text = ui.label('Checking...').classes('text-[11px] font-mono text-slate-400')
                lm_model_label = ui.label('Model: N/A').classes('text-[10px] font-mono text-slate-500 mb-4 truncate w-full')
                cpu_label = ui.label('CPU: 0%').classes('text-[11px] font-mono text-slate-400')
                ram_label = ui.label('RAM: 0%').classes('text-[11px] font-mono text-slate-400')

        ui.button('SHUTDOWN', on_click=app.shutdown).props('flat icon=power_settings_new color=red-4').classes('w-full mt-auto mb-4 px-4')

    # --- ヘッダー ---
    with ui.header().classes('bg-white text-slate-900 p-4 border-b flex justify-between shadow-none'):
        with ui.row().classes('items-center gap-4'):
            ui.button(icon='menu', on_click=drawer.toggle).props('flat round color=slate-900')
            ui.label(APP_NAME).classes('text-lg font-black uppercase')
        idx_label = ui.label(f'IDX: {backend.stats["total_chunks"]}').classes('text-[10px] font-mono text-slate-500')

    chat_results = ui.column().classes('w-full max-w-4xl mx-auto p-8 pb-40 gap-4')

    # --- ヘルパー ---
    def refresh_explorer(highlight_files=None):
        highlight_files = highlight_files or []
        tree_container.clear()
        def build_nodes(path: Path, relative_to: Path):
            rel = str(path.relative_to(relative_to)) if path != relative_to else ""
            node = {"id": rel if path.is_file() else None, "label": path.name, "class": "hit-file" if rel in highlight_files else ""}
            if path.is_dir():
                node["children"] = [build_nodes(p, relative_to) for p in sorted(path.iterdir())
                                    if not p.name.startswith('.') and (p.is_dir() or p.suffix in {".py", ".cs", ".cpp", ".h", ".json"})]
                node["icon"] = "folder"
            else: node["icon"] = "description"
            return node
        try:
            root = Path(backend.target_dir)
            tree_data = [build_nodes(root, root)]
            with tree_container:
                t = ui.tree(nodes=tree_data, label_key='label', on_select=lambda e: open_preview(e.value)).props('dark dense')
                t.add_slot('default-header', '<div :class="props.node.class">{{ props.node.label }}</div>')
        except: pass

    async def update_status_loop():
        while True:
            cpu_label.set_text(f"CPU: {psutil.cpu_percent()}%")
            ram_label.set_text(f"RAM: {psutil.virtual_memory().percent}%")
            connected = await backend.check_lm_studio()
            lm_indicator.props(f'color={"green" if connected else "red"}')
            lm_status_text.set_text(f'LM Studio: {"OK" if connected else "ERR"}')
            lm_model_label.set_text(f'Model: {backend.stats["model"]}')
            await asyncio.sleep(3)

    async def handle_query():
        query = input_field.value.strip()
        if not query: return
        input_field.value = ''
        with chat_results:
            ui.label(f"Q: {query}").classes('text-indigo-600 font-bold text-sm bg-indigo-50 p-2 w-full border-l-4 border-indigo-600')
            md = ui.markdown('Thinking...').classes('text-slate-700 text-sm p-4 w-full border-b')
            source_row = ui.row().classes('gap-2 mt-1')
        try:
            retriever = backend.get_retriever()
            docs = await run.io_bound(retriever.invoke, query)
            hits = list(set([d.metadata['source'] for d in docs]))
            refresh_explorer(highlight_files=hits)
            with source_row:
                for p in hits:
                    ui.button(p, on_click=lambda e, path=p: open_preview(path)).props('outline dense size=xs').classes('text-[10px] text-slate-500')
            context = "\n".join([f"FILE: {d.metadata['source']}\n{d.page_content}" for d in docs])
            llm = ChatOpenAI(base_url=backend.lm_studio_url, api_key="lm-studio", streaming=True)
            chain = ChatPromptTemplate.from_template("Context:\n{c}\n\nQ: {i}") | llm | StrOutputParser()
            full = ""
            async for chunk in chain.astream({"c": context, "i": query}):
                full += chunk
                md.set_content(full)
                ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')
        # except: md.set_content("Connection Error.")
        except Exception as e:
            # 接続エラーの理由をターミナル（黒い画面）に表示
            print(f"Connection Error Detail: {e}")

    with ui.footer().classes('bg-transparent'):
        with ui.row().classes('w-full max-w-4xl mx-auto p-4 bg-white border border-slate-300 items-end gap-2 shadow-lg rounded-t-xl'):
            input_field = ui.textarea(placeholder='Ask...').classes('flex-grow text-sm').props('borderless autogrow')
            ui.button(on_click=handle_query).props('flat icon=send color=indigo-600')

    def save_settings(v):
        app.storage.user['target_dir'] = v
        backend.target_dir = v
        refresh_explorer()

    async def rebuild_task():
        rebuild_btn.classes(add='rebuild-active')
        await run.io_bound(backend.rebuild_db)
        rebuild_btn.classes(remove='rebuild-active')
        idx_label.set_text(f'IDX: {backend.stats["total_chunks"]}')
        refresh_explorer()

    backend.load_db()
    refresh_explorer()
    asyncio.create_task(update_status_loop())

ui.run(title=APP_NAME, storage_secret='sentinel_secret_key')
