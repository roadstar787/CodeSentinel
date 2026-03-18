# 必要なライブラリをインポートします。
import os         # オペレーティングシステム機能
import sys        # システム固有のパラメータと機能
import asyncio    # 非同期プログラミング
import json       # JSON形式のデータ処理
import uuid       # ユニークID生成
from datetime import datetime # 日時操作
import psutil     # システム監視（CPU, RAMなど）
import httpx      # 非同期HTTPクライアント
from pathlib import Path  # オブジェクト指向パス操作
from collections import Counter  # コレクション（ヒット数カウント用）
from nicegui import ui, run, app  # NiceGUIフレームワーク
from langchain_core.prompts import ChatPromptTemplate  # LangChainプロンプトテンプレート
from langchain_core.output_parsers import StrOutputParser  # LangChain出力パーサー
from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # OpenAIチャットモデルと埋め込み（LM Studio互換）
from langchain_community.vectorstores import FAISS  # FAISSベクトルストア
from langchain_text_splitters import RecursiveCharacterTextSplitter  # テキスト分割
from langchain_community.document_loaders import (
    TextLoader, 
    PyPDFLoader, 
    UnstructuredMarkdownLoader, 
    UnstructuredExcelLoader, 
    UnstructuredPowerPointLoader
)  # 各種ファイルローダー

# --- システム設定 ---
# アプリケーションの名前
APP_NAME = "CodeSentinel"
# アプリケーションのバージョン
APP_VERSION = "0.3.7"

# RAG（Retrieval-Augmented Generation）のバックエンド処理を管理するクラス
class RAGBackend:
    # クラスの初期化
    def __init__(self):
        # ドキュメントの検索対象ディレクトリ
        self.target_dir = r"E:\sample\json"
        # 仕様書などのドキュメントディレクトリ
        self.doc_dir = r""
        # FAISSインデックスの保存パス
        self.db_path = "faiss_index_code"
        # LM StudioのAPIエンドポイントURL
        self.lm_studio_url = "http://localhost:1234/v1"
        # 動作モード (Normal or GapAnalysis)
        self.mode = "Normal"
        # チャット履歴の保存ディレクトリ
        self.chat_dir = Path("chat_history")
        self.chat_dir.mkdir(exist_ok=True)
        # ベクトルストアのインスタンス
        self.vectorstore = None
        # テキスト埋め込みモデルの設定
        self.embeddings = OpenAIEmbeddings(
            base_url=self.lm_studio_url,  # LM StudioのベースURL
            api_key="lm-studio",  # LM Studio用のダミーAPIキー
            check_embedding_ctx_length=False  # 埋め込みコンテキスト長のチェックを無効化
        )
        # RAGバックエンドの統計情報
        self.stats = {"total_chunks": 0, "is_rebuilding": False, "lm_connected": False, "model": "N/A"}

    # LM Studioへの接続を確認し、モデル情報を取得する非同期メソッド
    async def check_lm_studio(self):
        try:
            async with httpx.AsyncClient() as client:
                # タイムアウトを少し伸ばす
                resp = await client.get(f"{self.lm_studio_url}/models", timeout=30.0)
                if resp.status_code == 200:
                    # 接続成功
                    self.stats["lm_connected"] = True
                    data = resp.json()
                    if data.get('data'):
                        self.stats["model"] = data['data'][0]['id']  # モデルIDを取得
                    return True
                else:
                    # LM Studioがエラーを返した場合
                    print(f"LM Studio returned status: {resp.status_code}")
        except Exception as e:
            # 接続エラーの理由をターミナル（黒い画面）に表示
            print(f"Connection Error Detail: {e}")

        # 接続失敗
        self.stats["lm_connected"] = False
        return False
    
    # FAISSベクトルストアをロードするメソッド
    def load_db(self):
        if os.path.exists(self.db_path):
            try:
                # ローカルからベクトルストアをロード
                self.vectorstore = FAISS.load_local(self.db_path, self.embeddings, allow_dangerous_deserialization=True)
                self.stats["total_chunks"] = self.vectorstore.index.ntotal  # チャンク総数を更新
                return True
            except: 
                # ロード失敗
                return False
        return False

    # --- チャット履歴管理メソッド ---
    def list_chats(self):
        """保存されているチャット履歴の一覧を取得"""
        chats = []
        for f in self.chat_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as j:
                    data = json.load(j)
                    chats.append({
                        "id": f.stem,
                        "title": data.get("title", "Untitled Chat"),
                        "date": data.get("date", "")
                    })
            except: continue
        return sorted(chats, key=lambda x: x["date"], reverse=True)

    def load_chat(self, chat_id):
        """特定のチャット履歴をロード"""
        path = self.chat_dir / f"{chat_id}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def save_chat(self, chat_id, messages, title=None):
        """チャット履歴を保存"""
        path = self.chat_dir / f"{chat_id}.json"
        # 既存のデータを読み込んでタイトルを保持
        existing_title = "New Chat"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    existing_title = old_data.get("title", existing_title)
            except: pass
        
        data = {
            "title": title if title else existing_title,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": messages
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def delete_chat(self, chat_id):
        """チャット履歴を削除"""
        path = self.chat_dir / f"{chat_id}.json"
        if path.exists():
            path.unlink()

    # --- 抜けていたメソッドを修正 ---
    # ドキュメントリトリーバーを取得するメソッド
    def get_retriever(self):
        if self.vectorstore:
            return self.vectorstore.as_retriever(search_kwargs={"k": 10})  # 上位10件を検索（rag_web_ui準拠で増加）
        return None
    
    # ベクトルストアを再構築するメソッド
    def rebuild_db(self):
        self.stats["is_rebuilding"] = True  # 再構築中フラグを立てる
        docs = []
        
        # チャンク分割設定
        code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200, chunk_overlap=200,
            separators=["\nclass ", "\ndef ", "\nvoid ", "\nint ", "\nstatic ", "\n\n", "\n", " ", ""]
        )
        doc_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

        # 処理対象の設定
        targets = [
            {"path": self.target_dir, "type": "code", "exts": {".hpp", ".h", ".cpp", ".py", ".json", ".cs"}},
            {"path": self.doc_dir, "type": "document", "exts": {".pdf", ".md", ".xlsx", ".pptx"}}
        ]

        try:
            for target in targets:
                path_str = str(target["path"])
                if not path_str: continue
                base_path = Path(path_str)
                if not base_path.exists(): continue
                
                # ファイルを再帰的に検索
                files = [p for p in base_path.rglob('*') if p.suffix.lower() in target["exts"] and ".venv" not in p.parts and ".git" not in p.parts]
                
                for p in files:
                    try:
                        ext = p.suffix.lower()
                        if ext in {".py", ".cpp", ".h", ".hpp", ".cs", ".json"}:
                            loader = TextLoader(str(p), encoding="utf-8")
                        elif ext == ".pdf":
                            loader = PyPDFLoader(str(p))
                        elif ext == ".md":
                            loader = UnstructuredMarkdownLoader(str(p))
                        elif ext == ".xlsx":
                            loader = UnstructuredExcelLoader(str(p))
                        elif ext == ".pptx":
                            loader = UnstructuredPowerPointLoader(str(p))
                        else:
                            continue

                        raw = loader.load()
                        for d in raw:
                            d.metadata["source"] = str(p.relative_to(base_path))
                            d.metadata["type"] = target["type"] # 区分けを追加
                        
                        splitter = code_splitter if target["type"] == "code" else doc_splitter
                        docs.extend(splitter.split_documents(raw))
                    except Exception as e:
                        print(f"Error loading {p}: {e}")
                        continue
            
            if not docs:
                return False, "No documents found"

            # FAISSベクトルストアをドキュメントから構築
            self.vectorstore = FAISS.from_documents(docs, self.embeddings)
            # ベクトルストアをローカルに保存
            self.vectorstore.save_local(self.db_path)
            self.stats["total_chunks"] = len(docs)  # チャンク総数を更新
            return True, "SUCCESS"
        finally: 
            self.stats["is_rebuilding"] = False  # 再構築完了後フラグを下ろす

backend = RAGBackend()

# メインページを定義します。NiceGUIのルート ('/') に関連付けられます。
@ui.page('/')
async def main_page():
    # ユーザー設定からターゲットディレクトリをロード。設定がなければRAGBackendのデフォルトを使用。
    backend.target_dir = app.storage.user.get('target_dir', backend.target_dir)
    backend.doc_dir = app.storage.user.get('doc_dir', backend.doc_dir)
    backend.mode = app.storage.user.get('mode', 'Normal')
    
    # チャットセッション管理
    session = {'id': app.storage.user.get('current_chat_id', str(uuid.uuid4())), 'history': []}
    chat_data = backend.load_chat(session['id'])
    if chat_data: session['history'] = chat_data.get('messages', [])

    # 検索状態の管理（ヒット数など）
    state = {'hit_counts': Counter()}

    # カスタムCSSスタイルをページのheadに追加します。
    ui.add_head_html('''
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            .hit-file { font-weight: bold; }
            .rebuild-active { animation: pulse 1.5s infinite; color: #fbbf24 !important; border-color: #fbbf24 !important; }
            @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
            /* モダンチャットUI用 */
            .chat-bubble { font-family: "Inter", sans-serif; font-size: 0.95rem; line-height: 1.7; border-radius: 1.25rem; }
            .code-preview { background-color: #0d1117 !important; border-radius: 8px; color: #e6edf3; }
            .code-preview pre, .code-preview code { font-family: "JetBrains Mono", monospace !important; font-size: 13px !important; }
            /* Prismの背景と余白を完全に除去して親に合わせる */
            .code-preview .nicegui-code { padding: 0 !important; background: transparent !important; }
            .code-preview .nicegui-code pre { background: transparent !important; margin: 0 !important; padding: 0 !important; color: inherit !important; overflow: visible !important; }
            .line-numbers-col { 
                border-right: 1px solid #30363d; 
                color: #6e7681; 
                text-align: right; 
                padding-right: 12px !important; 
                user-select: none;
                line-height: 20px; /* 重要: コードの行高さと合わせる */
            }
            .code-col {
                padding-left: 12px !important;
                line-height: 20px; /* 重要: 行番号と合わせる */
            }
        </style>
    ''')

    # --- プレビューダイアログ ---
    # ファイルの内容を表示するためのダイアログ
    with ui.dialog() as preview_dialog, ui.card().classes('w-[80vw] max-w-4xl h-[80vh] p-0') as card:
        with ui.row().classes('w-full items-center p-4 bg-slate-50 border-b gap-4'):
            # プレビューダイアログのタイトル
            preview_title = ui.label('').classes('text-sm font-bold flex-grow text-slate-700')
            # 検索入力
            preview_search = ui.input(placeholder='Search...').props('dense outlined clearable').classes('w-48 text-xs')
            preview_search.on('keydown.enter', lambda: search_in_preview())
            ui.button(icon='search', on_click=lambda: search_in_preview()).props('flat round dense color=slate-400')
            # ダイアログを閉じるボタン
            ui.button(icon='close', on_click=preview_dialog.close).props('flat round dense color=slate-400')
        
        # プレビューするコードを表示するスクロール可能なエリア
        with ui.scroll_area().classes('w-full flex-grow code-preview p-4') as preview_scroll:
            # コード表示用コンテナ (動的に再生成するため)
            preview_code_box = ui.column().classes('w-full')

    # プレビュー内検索の状態管理
    search_state = {'last_query': '', 'last_index': -1, 'full_content': ''}

    def search_in_preview():
        query = str(preview_search.value or "")
        if not query: return
        content = str(search_state.get('full_content', ""))
        if not content: return
        lines = content.splitlines()
        
        # 次のヒット箇所を探す (循環検索)
        last_idx = int(search_state.get('last_index', -1))
        last_q = str(search_state.get('last_query', ""))
        start_idx = last_idx + 1 if query == last_q else 0
        
        found = False
        for i in range(len(lines)):
            idx = (start_idx + i) % len(lines)
            if query.lower() in lines[idx].lower():
                # ヒット！スクロール実行 (1行あたり約20pxの概算)
                line_height = 20 
                preview_scroll.scroll_to(pixels=idx * line_height)
                search_state['last_index'] = idx
                search_state['last_query'] = query
                ui.notify(f"Found on line {idx + 1}", color='indigo', pos='top')
                found = True
                break
        if not found:
            ui.notify("Not found", color='orange', pos='top')
            search_state['last_index'] = -1

    # ファイルプレビューを開く関数
    def open_preview(file_path, base_dir=None):
        # ファイルパスが指定されていなければ何もしない
        if not file_path: return
        # 基準ディレクトリを決定
        base = base_dir if base_dir else backend.target_dir
        # フルパスを作成
        full_path = Path(base) / file_path
        # フルパスがファイルでなければ何もしない
        if not full_path.is_file(): return
        try:
            # ファイルの内容をUTF-8で読み込み
            content = full_path.read_text(encoding='utf-8')
            search_state['full_content'] = content
            search_state['last_index'] = -1
            # プレビュータイトルを設定
            preview_title.set_text(f"{file_path}")
            # 言語指定 (ファイル拡張子に基づいてシンタックスハイライト)
            ext = full_path.suffix.lower()[1:] or 'text'
            
            preview_code_box.clear()
            with preview_code_box:
                # PDFやExcelはテキストとして見れない場合があるので分岐
                if ext in {'pdf', 'xlsx', 'pptx'}:
                    ui.label(f"Binary file ({ext}) cannot be previewed as text.").classes('text-slate-400 italic')
                else:
                    lines = content.splitlines()
                    ln_width = max(2, len(str(len(lines))))
                    ln_text = "\n".join(str(i+1) for i in range(len(lines)))
                    
                    with ui.row().classes('w-full gap-0 items-start no-wrap'):
                        # 行番号列
                        ui.label(ln_text).classes('line-numbers-col jetbrains-mono text-xs').style(f'width: {ln_width + 2}ch; white-space: pre;')
                        # コード列
                        ui.code(content, language=ext).classes('code-col flex-grow jetbrains-mono text-xs bg-transparent p-0')
            
            # プレビューダイアログを開く
            preview_dialog.open()
            preview_scroll.scroll_to(pixels=0)
        except Exception as e:
            # ファイル読み込みエラーを通知
            ui.notify(f"Read Error: {e}", color='red')

    # --- サイドバー (復活) ---
    # アプリケーションのサイドバー（左ドロワー）
    # with ui.left_drawer(fixed=True).classes('p-0 bg-[#0a0f18]') as drawer:
    with ui.left_drawer(fixed=True).classes('p-0 bg-[#2d3748]') as drawer:
        # サイドバー内のタブナビゲーション
        with ui.tabs().classes('w-full text-slate-500') as tabs:
            tab_exp = ui.tab('EXP', icon='account_tree')  # エクスプローラータブ
            tab_cht = ui.tab('CHATS', icon='chat')  # チャット履歴タブ
            tab_set = ui.tab('SET', icon='settings')  # 設定タブ
            tab_sts = ui.tab('STS', icon='hub')  # ステータスタブ

        # タブの内容パネル
        with ui.tab_panels(tabs, value=tab_exp).classes('w-full bg-transparent p-4'):
            # エクスプローラータブの内容
            with ui.tab_panel(tab_exp):
                ui.label('EXPLORER').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
                # ファイルツリーを表示するコンテナ
                tree_container = ui.column().classes('w-full gap-0')

            # チャット履歴タブの内容
            with ui.tab_panel(tab_cht):
                with ui.row().classes('w-full items-center justify-between mb-4'):
                    ui.label('HISTORY').classes('text-[10px] text-slate-600 tracking-widest')
                    ui.button(icon='add', on_click=lambda: start_new_chat()).props('flat round dense color=slate-400')
                chat_list_container = ui.column().classes('w-full gap-2')

            # 設定タブの内容
            with ui.tab_panel(tab_set):
                ui.label('CONFIG').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
                # ターゲットディレクトリのパス入力フィールド
                path_input = ui.input('Code Path', value=backend.target_dir).props('dark dense outlined').classes('w-full mb-2')
                # ドキュメントディレクトリのパス入力フィールド
                doc_path_input = ui.input('Doc Path', value=backend.doc_dir).props('dark dense outlined').classes('w-full mb-4')
                # パスを保存するボタン
                ui.button('SAVE PATHS', on_click=lambda: save_settings(path_input.value, doc_path_input.value)).props('flat border').classes('w-full text-xs mb-4')
                # ベクトルストアを再構築するボタン
                rebuild_btn = ui.button('REBUILD', on_click=lambda: rebuild_task()).props('flat icon=refresh').classes('w-full border border-slate-800 text-xs')

            # システムステータスタブの内容
            with ui.tab_panel(tab_sts):
                ui.label('SYSTEM').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
                # LM Studioの接続状態インジケーター
                with ui.row().classes('items-center gap-2 mb-2'):
                    lm_indicator = ui.icon('circle', color='grey').classes('text-[12px]')
                    lm_status_text = ui.label('Checking...').classes('text-[11px] font-mono text-slate-400')
                # 現在使用中のLM Studioモデル名
                lm_model_label = ui.label('Model: N/A').classes('text-[10px] font-mono text-slate-500 mb-4 truncate w-full')
                # CPU使用率表示
                cpu_label = ui.label('CPU: 0%').classes('text-[11px] font-mono text-slate-400')
                # RAM使用率表示
                ram_label = ui.label('RAM: 0%').classes('text-[11px] font-mono text-slate-400')

        # アプリケーションをシャットダウンするボタン
        ui.button('SHUTDOWN', on_click=app.shutdown).props('flat icon=power_settings_new color=red-4').classes('w-full mt-auto mb-4 px-4')

    # --- ヘッダー ---
    with ui.header().classes('bg-white text-slate-900 p-4 border-b flex justify-between shadow-none'):
        with ui.row().classes('items-center gap-4'):
            ui.button(icon='menu', on_click=drawer.toggle).props('flat round color=slate-900')
            with ui.row().classes('items-baseline gap-2'):
                ui.label(APP_NAME).classes('text-lg font-black uppercase')
                ui.label(f'v{APP_VERSION}').classes('text-[10px] font-mono text-slate-400')
        with ui.row().classes('items-center gap-2'):
            ui.label('MODE:').classes('text-[10px] text-slate-400')
            mode_toggle = ui.toggle({'Normal': 'Q&A', 'Gap': 'GAP'}, value=backend.mode, on_change=lambda e: change_mode(e.value)).props('dense unelevated toggle-color=indigo-600 color=slate-200 text-color=slate-600').classes('text-[10px]')
            idx_label = ui.label(f'IDX: {backend.stats["total_chunks"]}').classes('text-[10px] font-mono text-slate-500')

    chat_results = ui.column().classes('w-full max-w-4xl mx-auto p-8 pb-40 gap-4')

    # --- ヘルパー ---
    def refresh_explorer():
        tree_container.clear()
        def build_nodes(path: Path, relative_to: Path):
            rel = str(path.relative_to(relative_to)) if path != relative_to else ""
            hits = state['hit_counts'].get(rel, 0)
            hit_label = f" • {hits}" if hits > 0 else ""
            bg_style = f"background: rgba(99, 102, 241, {min(hits * 0.15, 0.4)});" if hits > 0 else ""
            
            node = {"id": rel if path.is_file() else None, "label": path.name + hit_label, "class": "hit-file" if hits > 0 else "", "style": bg_style}
            if path.is_dir():
                # 表示対象の拡張子 $(SUPPORTED_EXTS)
                supported = {".py", ".cs", ".cpp", ".h", ".hpp", ".json", ".pdf", ".md", ".xlsx", ".pptx"}
                node["children"] = [build_nodes(p, relative_to) for p in sorted(path.iterdir())
                                    if not p.name.startswith('.') and (p.is_dir() or p.suffix.lower() in supported)]
                node["icon"] = "folder"
            else:
                ext = path.suffix.lower()
                if ext == ".pdf": node["icon"] = "picture_as_pdf"
                elif ext in {".xlsx", ".xls"}: node["icon"] = "table_view"
                elif ext == ".pptx": node["icon"] = "present_to_all"
                elif ext == ".md": node["icon"] = "article"
                else: node["icon"] = "description"
            return node
        try:
            # Code Directory
            root = Path(backend.target_dir)
            if root.exists():
                # ルートフォルダ自体をトップレベルノードにする
                tree_data = [build_nodes(root, root)]
                with tree_container:
                    ui.label('CODE').classes('text-[9px] text-slate-500 mt-2 uppercase tracking-tighter')
                    t = ui.tree(nodes=tree_data, label_key='label', on_select=lambda e: open_preview(e.value, backend.target_dir)).props('dark dense expand-all')
                    t.add_slot('default-header', '<div :class="props.node.class" :style="props.node.style" style="border-radius: 4px; padding: 2px 6px;">{{ props.node.label }}</div>')
            
            # Document Directory
            if backend.doc_dir:
                doc_root = Path(backend.doc_dir)
                if doc_root.exists():
                    # ドキュメントルートも表示
                    doc_tree_data = [build_nodes(doc_root, doc_root)]
                    with tree_container:
                        ui.label('DOCS').classes('text-[9px] text-slate-500 mt-2 uppercase tracking-tighter')
                        t_doc = ui.tree(nodes=doc_tree_data, label_key='label', on_select=lambda e: open_preview(e.value, backend.doc_dir)).props('dark dense expand-all')
                        t_doc.add_slot('default-header', '<div :class="props.node.class" :style="props.node.style" style="border-radius: 4px; padding: 2px 6px;">{{ props.node.label }}</div>')
        except Exception as e:
            print(f"Explorer Refresh Error: {e}")

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
        
        # 履歴に追加
        session['history'].append({"role": "user", "content": query})

        with chat_results:
            ui.label(f"Q: {query}").classes('text-indigo-600 font-bold text-sm bg-indigo-50 p-2 w-full border-l-4 border-indigo-600')
            md = ui.markdown('Thinking...').classes('text-slate-700 text-sm p-4 w-full border-b')
            source_row = ui.row().classes('gap-2 mt-1')

        try:
            retriever = backend.get_retriever()
            if not retriever:
                md.set_content("Database not loaded.")
                return
            docs = await run.io_bound(retriever.invoke, query)
            hits = [d.metadata['source'] for d in docs]
            state['hit_counts'] = Counter(hits)
            refresh_explorer()
            
            unique_hits = []
            seen = set()
            for d in docs:
                pair = (d.metadata['source'], d.metadata.get('type', 'code'))
                if pair not in seen:
                    unique_hits.append(pair)
                    seen.add(pair)

            with source_row:
                for p, t in unique_hits:
                    b_dir = backend.target_dir if t == 'code' else backend.doc_dir
                    ui.button(p, on_click=lambda e, path=p, bd=b_dir: open_preview(path, bd)).props('outline dense size=xs').classes('text-[10px] text-indigo-500 border-indigo-200 bg-indigo-50')
            
            context = "\n".join([f"TYPE: {d.metadata.get('type','unknown')}\nFILE: {d.metadata['source']}\n{d.page_content}" for d in docs])
            llm = ChatOpenAI(base_url=backend.lm_studio_url, api_key="lm-studio", temperature=0.1, streaming=True)
            
            if backend.mode == 'Gap':
                prompt = """あなたは優秀なソフトウェアエンジニア兼テクニカルドキュメントアナリストです。
提供されたコンテキストには、仕様書などのドキュメント(TYPE: document)と、ソースコード(TYPE: code)の両方が含まれている可能性があります。

Q: {i}

【指示】
1. 仕様書(document)に記載されている内容と、実際のソースコード(code)を比較してください。
2. 仕様にあるが実装されていない項目、または仕様と実装が矛盾している箇所を特定してください。
3. 回答は日本語で、具体的なファイル名や仕様書の内容を引用して論理的に説明してください。

Context:
{c}
"""
            else:
                prompt = "回答は日本語で行ってください。\n\nContext:\n{c}\n\nQ: {i}"

            chain = ChatPromptTemplate.from_template(prompt) | llm | StrOutputParser()
            full = ""
            async for chunk in chain.astream({"c": context, "i": query}):
                full += chunk
                md.set_content(full)
                ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')
            
            # コピーボタンを追加
            with chat_results:
                ui.button('COPY MARKDOWN', icon='content_copy', on_click=lambda f=full: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(f)})')) \
                    .props('flat dense color=slate-400 size=sm').classes('self-end mt-[-10px] mb-4 opacity-50 hover:opacity-100')
            
            # 履歴に追加して保存
            session['history'].append({"role": "ai", "content": full, "sources": unique_hits})
            title = query[:20] + ("..." if len(query) > 20 else "")
            backend.save_chat(session['id'], session['history'], title if len(session['history']) <= 2 else None)
            refresh_chat_list()

        except Exception as e:
            md.set_content(f"Error: {str(e)}")
            print(f"Error Detail: {e}")

    def refresh_chat_list():
        chat_list_container.clear()
        chats = backend.list_chats()
        with chat_list_container:
            if not chats:
                ui.label('No history').classes('text-[10px] text-slate-500 italic p-2')
            for c in chats:
                with ui.row().classes('w-full items-center gap-1 group'):
                    # チャット選択ボタン
                    # クロージャの副作用を避けるため lambda の引数にデフォルト値を設定
                    btn = ui.button(on_click=lambda e, cid=c['id']: load_chat_session(cid)).props('flat no-caps dense').classes('flex-grow text-left justify-start px-2 py-1 rounded hover:bg-slate-700/50')
                    with btn:
                        with ui.column().classes('gap-0'):
                            ui.label(c['title']).classes('text-xs text-slate-200 line-clamp-1')
                            ui.label(c['date']).classes('text-[9px] text-slate-500')
                    # 削除ボタン
                    ui.button(icon='delete', on_click=lambda e, cid=c['id']: delete_chat_session(cid)).props('flat round dense size=sm color=red-4').classes('opacity-0 group-hover:opacity-100 transition-opacity')

    def load_chat_session(chat_id):
        data = backend.load_chat(chat_id)
        if not data: return
        session['id'] = chat_id
        session['history'] = data.get('messages', [])
        app.storage.user['current_chat_id'] = chat_id
        
        chat_results.clear()
        with chat_results:
            for msg in session['history']:
                if msg['role'] == 'user':
                    ui.label(f"Q: {msg['content']}").classes('text-indigo-600 font-bold text-sm bg-indigo-50 p-2 w-full border-l-4 border-indigo-600')
                else:
                    ui.markdown(msg['content']).classes('text-slate-700 text-sm p-4 w-full border-b')
                    # 保存された履歴からもコピーボタンを表示
                    ui.button('COPY MARKDOWN', icon='content_copy', on_click=lambda f=msg['content']: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(f)})')) \
                        .props('flat dense color=slate-400 size=sm').classes('self-end mt-[-10px] mb-4 opacity-50 hover:opacity-100')
                    
                    if msg.get('sources'):
                        with ui.row().classes('gap-2 mt-1'):
                            for p, t in msg['sources']:
                                b_dir = backend.target_dir if t == 'code' else backend.doc_dir
                                ui.button(p, on_click=lambda e, path=p, bd=b_dir: open_preview(path, bd)).props('outline dense size=xs').classes('text-[10px] text-indigo-500 border-indigo-200 bg-indigo-50')
        ui.notify(f"Chat loaded: {data['title']}")
        refresh_chat_list()

    def start_new_chat():
        new_id = str(uuid.uuid4())
        session['id'] = new_id
        session['history'] = []
        app.storage.user['current_chat_id'] = new_id
        chat_results.clear()
        ui.notify("New chat started")
        refresh_chat_list()

    def delete_chat_session(chat_id):
        backend.delete_chat(chat_id)
        if session['id'] == chat_id:
            start_new_chat()
        else:
            refresh_chat_list()
        ui.notify("Chat deleted")

    with ui.footer().classes('bg-transparent'):
        with ui.row().classes('w-full max-w-4xl mx-auto p-4 bg-white border border-slate-300 items-end gap-2 shadow-lg rounded-t-xl'):
            input_field = ui.textarea(placeholder='Ask...').classes('flex-grow text-sm').props('borderless autogrow')
            ui.button(on_click=handle_query).props('flat icon=send color=indigo-600')

    def save_settings(v_target, v_doc):
        app.storage.user['target_dir'] = v_target
        app.storage.user['doc_dir'] = v_doc
        backend.target_dir = v_target
        backend.doc_dir = v_doc
        refresh_explorer()

    def change_mode(v):
        app.storage.user['mode'] = v
        backend.mode = v
        ui.notify(f"Mode changed to: {v}")

    async def rebuild_task():
        # ボタンをアニメーション状態に変更
        rebuild_btn.classes(add='rebuild-active text-yellow-400 border-yellow-400 bg-yellow-900/20')
        rebuild_btn.classes(remove='border-slate-800')
        rebuild_btn.set_text('BUILDING...')
        
        # バックグラウンドで再構築を実行
        await run.io_bound(backend.rebuild_db)
        
        # アニメーション状態を解除してテキストを元に戻す
        rebuild_btn.classes(remove='rebuild-active text-yellow-400 border-yellow-400 bg-yellow-900/20')
        rebuild_btn.classes(add='border-slate-800')
        rebuild_btn.set_text('REBUILD')
        
        idx_label.set_text(f'IDX: {backend.stats["total_chunks"]}')
        refresh_explorer()

    backend.load_db()
    
    # 初期読込
    if session['history']:
        # 履歴がある場合は表示を復元
        load_chat_session(session['id'])
    
    refresh_explorer()
    refresh_chat_list()
    asyncio.create_task(update_status_loop())

ui.run(title=APP_NAME, storage_secret='sentinel_secret_key')
