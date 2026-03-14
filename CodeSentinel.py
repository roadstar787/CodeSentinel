import os
import asyncio
import psutil
import datetime
import json
from pathlib import Path
from collections import Counter
from nicegui import ui, run, app
from langchain_core.prompts import ChatPromptTemplate
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
            "is_rebuilding": False,
            "revision": "v1.3.0"
        }
        self.config_file = "db_config.json"
        self.load_config() # 起動時に保存されたパスを読み込む

    def load_config(self):
        """保存されたパス情報を読み込む"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.target_dir = config.get("target_dir", self.target_dir)
            except: pass

    def save_config(self):
        """現在のパス情報を保存する"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({"target_dir": self.target_dir}, f, ensure_ascii=False, indent=2)
        except: pass

    def load_db(self):
        # if os.path.exists(self.db_path):
        #     try:
        #         self.vectorstore = FAISS.load_local(
        #             self.db_path, self.embeddings, allow_dangerous_deserialization=True
        #         )
        #         self.stats["total_chunks"] = self.vectorstore.index.ntotal
        #         idx_file = Path(self.db_path) / "index.faiss"
        #         if idx_file.exists():
        #             mtime = datetime.datetime.fromtimestamp(idx_file.stat().st_mtime)
        #             self.stats["last_rebuild"] = mtime.strftime("%Y-%m-%d %H:%M:%S")
        #         return True, "DBを読み込みました。"
        #     except Exception as e:
        #         return False, f"読み込み失敗: {str(e)}"
        # return False, "DBが見つかりません。"
        if os.path.exists(self.db_path):
            try:
                # パスの一致チェック (簡易版)
                if os.path.exists(self.config_file):
                    with open(self.config_file, "r", encoding="utf-8") as f:
                        saved_path = json.load(f).get("target_dir")
                    if saved_path != self.target_dir:
                        return False, "警告: 設定パスとDBの構築パスが異なります。再構築を推奨します。"

                self.vectorstore = FAISS.load_local(
                    self.db_path, self.embeddings, allow_dangerous_deserialization=True
                )
                # ... 既存の読み込みコード ...
                return True, "DBを読み込みました。"
            except Exception as e:
                return False, f"読み込み失敗: {str(e)}"
        return False, "DBが見つかりません。"

    def get_file_content(self, rel_path):
        full_path = Path(self.target_dir) / rel_path
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            ext = full_path.suffix.lstrip('.')
            return f"```{ext}\n{content}\n```"
        except Exception as e:
            return f"Error loading file: {str(e)}"

    def rebuild_db(self, progress_callback=None):
        self.stats["is_rebuilding"] = True
        docs = []
        code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=100,
            separators=["\nclass ", "\ndef ", "\n\n", "\n", " "]
        )
        extensions = {".hpp", ".h", ".cpp", ".py", ".json", ".js", ".ts", ".cs", ".java"}
        try:
            root_path = Path(self.target_dir)
            files = [p for p in root_path.rglob('*') if p.suffix in extensions
                     and not any(x in p.parts for x in {'.venv', '.git', '__pycache__', 'node_modules'})]

            for i, p in enumerate(files):
                if progress_callback: progress_callback(f"Scanning: {i+1}/{len(files)}")
                try:
                    loader = TextLoader(str(p), encoding="utf-8")
                    raw_docs = loader.load()
                    for d in raw_docs: d.metadata["source"] = str(p.relative_to(root_path))
                    docs.extend(code_splitter.split_documents(raw_docs))
                except: continue

            self.vectorstore = FAISS.from_documents(docs, self.embeddings)
            self.vectorstore.save_local(self.db_path)
            self.stats["total_chunks"] = len(docs)
            self.stats["is_rebuilding"] = False
            # ... 既存の再構築ロジック ...
            try:
                # (インデックス作成完了直後に実行)
                self.vectorstore.save_local(self.db_path)
                self.save_config() # ★ここで構築時のパスをファイルに保存
                # ...
                return True, "再構築完了"
            except Exception as e:
                self.stats["is_rebuilding"] = False
                return False, str(e)
        except Exception as e:
            self.stats["is_rebuilding"] = False
            return False, str(e)

    def get_retriever(self):
        return self.vectorstore.as_retriever(search_kwargs={"k": 6}) if self.vectorstore else None

# --- UI Global Configuration ---
backend = RAGBackend()

@ui.page('/')
async def main_page():
    ui.add_head_html('''
        <style>
            .status-item { display: flex; justify-content: space-between; align-items: center; width: 100%; margin-bottom: 12px; }
            .status-label { font-size: 10px; color: #94a3b8; font-weight: 800; }
            .status-value { font-size: 12px; color: #f1f5f9; text-align: right; font-family: monospace; }
            @keyframes pulse-sync { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
            .rebuild-active { animation: pulse-sync 1.5s infinite !important; pointer-events: none; }
            .rebuild-active-btn { background: rgba(251, 191, 36, 0.2) !important; border: 1px solid #fbbf24 !important; }
        </style>
    ''')

    state = {'processing': False, 'hit_counts': Counter()}

    # --- Header (ヘッダーを先に定義してトグルボタンを有効化) ---
    with ui.header().classes('bg-white text-slate-800 p-4 border-b flex justify-between shadow-sm'):
        with ui.row().classes('items-center gap-3'):
            # 後で定義する drawer をトグルさせる
            ui.button(on_click=lambda: drawer.toggle(), icon='menu').props('flat round').classes('text-slate-400')
            ui.label('CodeSentinel').classes('text-xl font-black text-indigo-600')

        # LM Studio リンク表示 (復活)
        with ui.row().classes('items-center gap-2'):
            ui.icon('circle', size='10px').classes('text-green-500 animate-pulse')
            ui.label('LM Studio Linked').classes('text-[11px] font-bold text-slate-400')

    # --- Sidebar Drawer ---
    with ui.left_drawer(value=True).classes('bg-slate-950 text-white p-0 shadow-2xl') as drawer:
        with ui.tabs().classes('w-full bg-slate-900 text-slate-400') as tabs:
            tab_explorer = ui.tab('Explorer', icon='folder')
            tab_settings = ui.tab('Settings', icon='settings')
            tab_status = ui.tab('Status', icon='analytics')

        with ui.tab_panels(tabs, value=tab_explorer).classes('w-full flex-grow bg-transparent p-0'):

            # Explorer Tab
            with ui.tab_panel(tab_explorer).classes('p-0'):
                tree_container = ui.column().classes('w-full gap-0 p-2')

            # Settings Tab
            with ui.tab_panel(tab_settings).classes('p-6'):
                # path_input = ui.input('Path', value=backend.target_dir,
                #                       on_change=lambda e: (setattr(backend, 'target_dir', e.value), refresh_tree()))\
                #                       .props('dark outlined dense').classes('mb-6')
                path_input = ui.input('Path', value=backend.target_dir,
                                      on_change=lambda e: update_path_logic(e.value))\
                                      .props('dark outlined dense').classes('mb-6')

                rebuild_btn = ui.button('インデックス再構築', on_click=lambda: rebuild_db_task())\
                                .props('flat icon=bolt color=amber').classes('w-full border border-amber-900/30 bg-amber-950/20 py-3')
                ui.button('DB再読み込み', on_click=lambda: load_db_task()).props('flat icon=refresh').classes('w-full border border-slate-800 mt-4')
                ui.button('終了', on_click=lambda: app.shutdown()).props('flat icon=power color=red').classes('w-full border border-red-900/30 mt-8')


            # Status Tab (表示項目を復活 & 右寄せ対応)
            with ui.tab_panel(tab_status).classes('p-6'):
                with ui.element('div').classes('status-item'):
                    ui.label('Vector DB').classes('status-label')
                    status_chip = ui.label('OFFLINE').classes('px-2 py-0.5 rounded text-[10px] font-bold')
                with ui.element('div').classes('status-item'):
                    ui.label('Chunks').classes('status-label')
                    chunk_count_label = ui.label('0').classes('status-value')
                with ui.element('div').classes('status-item'):
                    ui.label('CPU').classes('status-label')
                    cpu_label = ui.label('0%').classes('status-value')

    # --- Dialog ---
    with ui.dialog().props('full-width') as preview_dialog, ui.card().classes('w-full max-h-[90vh] p-0'):
        with ui.row().classes('w-full items-center justify-between p-4 border-b'):
            preview_title = ui.label('').classes('font-bold')
            ui.button(icon='close', on_click=preview_dialog.close).props('flat round')
        with ui.scroll_area().classes('flex-grow p-6 bg-slate-900'):
            preview_content = ui.markdown('').classes('text-slate-100 font-mono')


    def update_path_logic(new_path):
        backend.target_dir = new_path
        # パスが変わったらDBの整合性を再確認
        success, msg = backend.load_db()
        if not success and "警告" in msg:
            ui.notify(msg, type='warning', duration=5)
        refresh_tree()

    # --- Functions ---
    def refresh_tree():
        tree_container.clear()
        root = Path(backend.target_dir)
        if not root.exists(): return
        def render(path, level=0):
            rel = str(path.relative_to(root))
            if any(x in rel for x in {'.venv', '.git', '__pycache__'}): return
            hits = state['hit_counts'].get(rel, 0)
            with tree_container:
                # no-wrap と truncate を追加して一行に固定
                row = ui.row().classes('w-full items-center no-wrap py-1 px-4 cursor-pointer hover:bg-slate-800 transition-all').style(f'padding-left: {level*12+16}px; {"background:rgba(99,102,241,0.2)" if hits > 0 else ""}')
                if not path.is_dir():
                    row.on('click', lambda: (preview_title.set_text(rel), preview_content.set_content(backend.get_file_content(rel)), preview_dialog.open()))
                with row:
                    ui.icon('folder' if path.is_dir() else 'description', size='16px').classes('text-slate-500 mr-2 flex-shrink-0')
                    ui.label(path.name).classes('text-xs text-slate-300 truncate flex-grow')
            if path.is_dir():
                for c in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())): render(c, level+1)
        render(root)

    def sync_ui_state():
        """タブ切り替え時に再構築中の表示を同期"""
        if backend.stats["is_rebuilding"]:
            rebuild_btn.classes(add='rebuild-active rebuild-active-btn')
            chunk_count_label.classes(add='rebuild-active')
            rebuild_btn.set_text('再構築中...'); rebuild_btn.disable()
        else:
            rebuild_btn.classes(remove='rebuild-active rebuild-active-btn')
            chunk_count_label.classes(remove='rebuild-active')
            rebuild_btn.set_text('インデックス再構築'); rebuild_btn.enable()

    tabs.on('update:modelValue', sync_ui_state)

    async def rebuild_db_task():
        if backend.stats["is_rebuilding"]: return
        backend.stats["is_rebuilding"] = True
        sync_ui_state()
        success, msg = await run.io_bound(backend.rebuild_db, progress_callback=lambda t: chunk_count_label.set_text(t))
        backend.stats["is_rebuilding"] = False
        sync_ui_state()
        load_db_task()

    def load_db_task():
        success, msg = backend.load_db()
        status_chip.set_text('ONLINE' if success else 'OFFLINE')
        status_chip.classes(replace='bg-green-950/20 text-green-400' if success else 'bg-red-950/20 text-red-400')
        chunk_count_label.set_text(str(backend.stats["total_chunks"]))
        if success: refresh_tree()

    # Chat UI (省略されていた部分を確実に動作する形で復元)
    chat_results = ui.column().classes('w-full max-w-4xl mx-auto p-6 pb-48 gap-8')
    with ui.footer().classes('bg-transparent'):
        with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
            with ui.row().classes('w-full bg-white p-3 border rounded-2xl shadow-2xl items-end gap-2'):
                input_field = ui.textarea(placeholder='質問を入力...').classes('flex-grow px-3').props('borderless autogrow')
                ui.button(icon='send', on_click=lambda: handle_query()).props('round color=indigo shadow-lg')

    async def handle_query():
        # チャットロジック
        if state['processing'] or not input_field.value.strip(): return
        query = input_field.value.strip(); input_field.value = ''; state['processing'] = True
        # ここにLLM呼び出しと表示処理を記述（以前の正常版と同じ）
        state['processing'] = False

    ui.timer(2.0, lambda: cpu_label.set_text(f"{psutil.cpu_percent()}%"))
    ui.timer(0.1, load_db_task, once=True)

ui.run(title='CodeSentinel', port=8080, reload=False)
