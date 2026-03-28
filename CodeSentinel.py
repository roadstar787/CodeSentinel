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
from config import Settings  # 設定モジュール
from todo_service import TodoService  # ToDoサービス

# --- システム設定 ---
# アプリケーションの名前
APP_NAME = "CodeSentinel"
# アプリケーションのバージョン
APP_VERSION = "0.4.0"

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
        # ToDoサービスの初期化
        self.todo_service = TodoService(Path("todo_history"))
        # RAGバックエンドの統計情報
        self.stats = {
            "total_chunks": 0, 
            "is_rebuilding": False, 
            "lm_connected": False, 
            "model": "N/A",
            "revision": "v0.3.8",
            "last_rebuild": "Never"
        }

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
    async def rebuild_db(self):
        self.stats["is_rebuilding"] = True  # 再構築中フラグを立てる
        docs = []
        
        # LM Studioへの接続を確認
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.lm_studio_url}/models", timeout=10.0)
                if resp.status_code != 200:
                    return False, f"LM Studio connection failed: {resp.status_code}"
        except Exception as e:
            return False, f"LM Studio connection error: {str(e)}"
        
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
                
                # ファイル数が多すぎないかチェック
                if len(files) > 10000:
                    return False, f"Too many files ({len(files)}). Please reduce the number of files."
                
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
                        chunks = splitter.split_documents(raw)
                        docs.extend(chunks)
                        
                        # メモリ使用量のチェック
                        import psutil
                        mem = psutil.virtual_memory()
                        if mem.percent > 90:
                            return False, f"High memory usage ({mem.percent}%). Please try with fewer files."
                            
                    except Exception as e:
                        print(f"Error loading {p}: {e}")
                        continue
            
            if not docs:
                return False, "No documents found"

            # ドキュメント数が多すぎないかチェック
            if len(docs) > 50000:
                return False, f"Too many document chunks ({len(docs)}). Please reduce the number of files."

            try:
                # FAISSベクトルストアをドキュメントから構築
                self.vectorstore = FAISS.from_documents(docs, self.embeddings)
                # ベクトルストアをローカルに保存
                self.vectorstore.save_local(self.db_path)
                self.stats["total_chunks"] = len(docs)  # チャンク総数を更新
                self.stats["last_rebuild"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return True, "SUCCESS"
            except Exception as e:
                return False, f"Failed to create vector store: {str(e)}"
                
        except Exception as e:
            return False, f"Unexpected error during rebuild: {str(e)}"
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
            .search-highlight-line {
                background-color: rgba(96, 165, 250, 0.2) !important;
                width: 100%;
                display: inline-block;
            }
            /* ステータス画面用スタイル (rag_web_ui.py 互換) */
            .status-item { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; width: 100%; }
            .status-label { font-size: 10px; color: #94a3b8; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; }
            .status-value { font-size: 12px; color: #f1f5f9; font-family: "JetBrains Mono", monospace; font-weight: 500; }
            
            /* Gap Analysis カードスタイル */
            .gap-card { 
                border-left: 4px solid #f87171; 
                background: #fef2f2; 
                padding: 12px; 
                border-radius: 8px; 
                margin-top: 8px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            }
            .gap-file { font-size: 0.75rem; font-weight: bold; color: #b91c1c; margin-bottom: 4px; }
            .gap-issue { font-size: 0.85rem; color: #450a0a; line-height: 1.5; }
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
        query = str(preview_search.value or "").strip()
        if not query: return
        content = str(search_state.get('full_content', ""))
        if not content: return
        lines = content.splitlines()
        
        # 次のヒット箇所を探す (循環検索)
        last_idx = int(search_state.get('last_index', -1))
        last_q = str(search_state.get('last_query', ""))
        start_idx = last_idx + 1 if query == last_q else 0
        
        found_idx = -1
        matches = [idx for idx, line in enumerate(lines) if query.lower() in line.lower()]
        total = len(matches)
        
        if total > 0:
            # 次のインデックスを計算
            if query == last_q:
                # すでにヒットしている場合、次のマッチを探す
                next_matches = [m for m in matches if m > last_idx]
                found_idx = next_matches[0] if next_matches else matches[0]
                match_no = matches.index(found_idx) + 1
            else:
                found_idx = matches[0]
                match_no = 1

            # ヒット！スクロール実行
            line_height = 20 
            preview_scroll.scroll_to(pixels=found_idx * line_height)
            
            search_state['last_index'] = found_idx
            search_state['last_query'] = query
            ui.notify(f"Match {match_no}/{total} (Line {found_idx + 1})", color='indigo', pos='top', duration=1000)
        else:
            ui.notify("No matches found", color='orange', pos='top')
            search_state['last_index'] = -1

    # ファイルプレビューを開く関数
    def open_preview(file_path, base_dir=None, jump_line=None):
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
            
            # 指定行があればスクロール
            if jump_line is not None:
                try:
                    line_idx = int(jump_line) - 1
                    line_height = 20
                    # ダイアログが開くのを少し待ってからスクロール
                    ui.timer(0.2, lambda: preview_scroll.scroll_to(pixels=line_idx * line_height), once=True)
                except: pass
            else:
                preview_scroll.scroll_to(pixels=0)
        except Exception as e:
            # ファイル読み込みエラーを通知
            ui.notify(f"Read Error: {e}", color='red')

    # --- サイドバー (復活) ---
    # アプリケーションのサイドバー（左ドロワー）
    with ui.left_drawer(fixed=True).classes('p-0 bg-[#2d3748]') as drawer:
        # サイドバー内のタブナビゲーション
        with ui.tabs().classes('w-full text-slate-500') as tabs:
            tab_exp = ui.tab('EXP', icon='account_tree')  # エクスプローラータブ
            tab_cht = ui.tab('CHATS', icon='chat')  # チャット履歴タブ
            tab_tod = ui.tab('TODOS', icon='check_box')  # ToDoリストタブ
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

            # ToDoリストタブの内容
            with ui.tab_panel(tab_tod):
                with ui.row().classes('w-full items-center justify-between mb-4'):
                    ui.label('TODOS').classes('text-[10px] text-slate-600 tracking-widest')
                    ui.button(icon='add', on_click=lambda: show_add_todo_dialog()).props('flat round dense color=slate-400')
                
                # ToDo統計情報
                todo_stats_container = ui.row().classes('w-full gap-4 mb-4')
                
                # ToDoリスト表示エリア
                todo_list_container = ui.column().classes('w-full gap-2')
                
                # ソートとフィルタリングコントロール
                with ui.row().classes('w-full items-center justify-between mb-2'):
                    with ui.row().classes('gap-2'):
                        # ソートオプション
                        sort_select = ui.select(
                            options={
                                'created_at_desc': '作成日時 (新しい順)',
                                'created_at_asc': '作成日時 (古い順)',
                                'updated_at_desc': '更新日時 (新しい順)',
                                'updated_at_asc': '更新日時 (古い順)',
                                'priority_desc': '優先度 (高→低)',
                                'priority_asc': '優先度 (低→高)',
                                'due_date_asc': '期限 (近い順)',
                            },
                            value='created_at_desc',
                            label='ソート',
                        ).props('dense outlined mini').classes('text-xs')
                        sort_select.on('change', lambda e: refresh_todo_list())
                    
                    # フィルタリングオプション
                    with ui.row().classes('gap-2'):
                        show_completed_toggle = ui.toggle(
                            options={True: '完了済みを表示', False: '未完了のみ'},
                            value=True,
                        ).props('dense mini').classes('text-xs')
                        show_completed_toggle.on('change', lambda e: refresh_todo_list())
                
                # リフレッシュボタン
                refresh_todo_btn = ui.button(icon='refresh', on_click=lambda: refresh_todo_list()).props('flat dense mini color=slate-400')

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
            with ui.tab_panel(tab_sts).classes('p-6'):
                ui.label('SYSTEM STATUS').classes('text-[10px] font-bold text-indigo-400 mb-4 tracking-widest')
                
                with ui.element('div').classes('status-item'):
                    ui.label('Revision').classes('status-label')
                    ui.label(backend.stats["revision"]).classes('status-value text-indigo-400')
                
                with ui.element('div').classes('status-item'):
                    ui.label('Vector DB').classes('status-label')
                    status_chip = ui.label('OFFLINE').classes('px-2 py-0.5 rounded text-[10px] font-bold')
                
                with ui.element('div').classes('status-item'):
                    ui.label('Total Chunks').classes('status-label')
                    chunk_count_label = ui.label(str(backend.stats["total_chunks"])).classes('status-value transition-all')
                
                with ui.element('div').classes('status-item'):
                    ui.label('Last Build').classes('status-label')
                    last_update_label = ui.label(backend.stats["last_rebuild"]).classes('status-value')

                ui.separator().classes('bg-slate-700 my-6 opacity-30')
                
                ui.label('SYSTEM LOAD').classes('text-[10px] font-bold text-indigo-400 mb-4 tracking-widest')
                
                # LM Studioの接続状態（Vector DBと同じ形式に統一）
                with ui.element('div').classes('status-item'):
                    ui.label('LM Studio').classes('status-label')
                    lm_status_chip = ui.label('Checking...').classes('px-2 py-0.5 rounded text-[10px] font-bold')
                
                # モデル名
                with ui.element('div').classes('status-item'):
                    ui.label('Active Model').classes('status-label')
                    lm_model_label = ui.label('N/A').classes('status-value truncate max-w-[120px]')

                # CPU使用率表示
                with ui.element('div').classes('status-item'):
                    ui.label('CPU').classes('status-label')
                    cpu_label = ui.label('0%').classes('status-value')
                
                # RAM使用率表示
                with ui.element('div').classes('status-item'):
                    ui.label('RAM').classes('status-label')
                    ram_label = ui.label('0GB').classes('status-value')

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
            cpu_label.set_text(f"{psutil.cpu_percent()}%")
            mem = psutil.virtual_memory()
            ram_label.set_text(f"{mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB")
            
            connected = await backend.check_lm_studio()
            # LM Studioの状態を更新（Vector DBと同じ形式に統一）
            lm_status_chip.set_text('ONLINE' if connected else 'OFFLINE')
            lm_status_chip.classes(replace='bg-green-900/40 text-green-400' if connected else 'bg-red-900/40 text-red-400')
            lm_model_label.set_text(backend.stats["model"])
            
            # DB状態の更新
            is_loaded = backend.vectorstore is not None
            status_chip.set_text('ONLINE' if is_loaded else 'OFFLINE')
            status_chip.classes(replace='bg-green-900/40 text-green-400' if is_loaded else 'bg-red-900/40 text-red-400')
            chunk_count_label.set_text(str(backend.stats["total_chunks"]))
            last_update_label.set_text(backend.stats["last_rebuild"])
            
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
提供されたコンテキストに基づいて、仕様書(document)とソースコード(code)を比較分析してください。

Q: {i}

【回答ガイドライン】
1. 仕様書(document)に記載されている内容と、実際のソースコード(code)を詳細に比較してください。
2. 仕様にあるが実装されていない項目、または仕様と実装が矛盾している箇所を特定してください。
3. 回答は日本語で、具体的なファイル名や仕様を引用して説明してください。

【重要：構造化データの出力】
回答の最後に、以下の形式で分析結果の要約を **必ず** 含めてください。
各項目は JSON 形式で `<gaps>` タグで囲んでください。
例:
<gaps>
[
  {{"file": "main.py", "line": 42, "issue": "仕様ではAとされていますが、実装はBになっています"}},
  {{"file": "utils.py", "line": 10, "issue": "仕様にある例外処理が実装されていません"}}
]
</gaps>

Context:
{c}
"""
            else:
                prompt = "回答は日本語で行ってください。\n\nContext:\n{c}\n\nQ: {i}"

            chain = ChatPromptTemplate.from_template(prompt) | llm | StrOutputParser()
            full = ""
            async for chunk in chain.astream({"c": context, "i": query}):
                full += chunk
                # <gaps> タグ以降を表示しないようにトリミング（後で構造化表示するため）
                display_text = full
                if "<gaps>" in full:
                    display_text = full.split("<gaps>")[0]
                md.set_content(display_text)
                ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')
            
            # Gap データの解析と可視化
            if backend.mode == 'Gap' and "<gaps>" in full:
                try:
                    gap_json_str = full.split("<gaps>")[1].split("</gaps>")[0].strip()
                    gaps = json.loads(gap_json_str)
                    if gaps:
                        with chat_results:
                            ui.label('ANALYSIS RESULTS (GAPS)').classes('text-[10px] text-red-500 font-bold mt-2 tracking-widest')
                            for gap in gaps:
                                f_path = gap.get("file", "Unknown")
                                l_num = gap.get("line")
                                issue = gap.get("issue", "Unknown")
                                with ui.element('div').classes('gap-card w-full'):
                                    with ui.row().classes('items-center justify-between w-full'):
                                        ui.label(f"FILE: {f_path} (Line {l_num})" if l_num else f"FILE: {f_path}").classes('gap-file')
                                        if f_path != "Unknown":
                                            ui.button('JUMP', icon='launch', on_click=lambda e, fp=f_path, ln=l_num: open_preview(fp, backend.target_dir, ln))\
                                                .props('flat dense size=xs color=red-7').classes('text-[9px]')
                                    ui.label(issue).classes('gap-issue')
                except Exception as e:
                    print(f"Gap Parse Error: {e}")

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

    # --- ToDo関連機能 ---
    def refresh_todo_stats():
        """ToDo統計情報を更新"""
        stats = backend.todo_service.get_todo_statistics()
        
        todo_stats_container.clear()
        with todo_stats_container:
            with ui.column().classes('items-center p-3 bg-slate-700/50 rounded-lg'):
                ui.label(f'総数: {stats["total"]}').classes('text-xs font-bold text-slate-300')
                with ui.row().classes('gap-4 mt-1'):
                    ui.label(f'未完了: {stats["pending"]}').classes('text-xs text-amber-400')
                    ui.label(f'完了: {stats["completed"]}').classes('text-xs text-green-400')
            
            # 優先度分布
            with ui.column().classes('items-center p-3 bg-slate-700/50 rounded-lg'):
                ui.label('優先度分布').classes('text-xs font-bold text-slate-300 mb-1')
                with ui.row().classes('gap-2'):
                    high_color = 'text-red-400' if stats["priority_distribution"]["high"] > 0 else 'text-slate-600'
                    ui.label(f'高: {stats["priority_distribution"]["high"]}').classes(f'text-xs {high_color}')
                    medium_color = 'text-yellow-400' if stats["priority_distribution"]["medium"] > 0 else 'text-slate-600'
                    ui.label(f'中: {stats["priority_distribution"]["medium"]}').classes(f'text-xs {medium_color}')
                    low_color = 'text-blue-400' if stats["priority_distribution"]["low"] > 0 else 'text-slate-600'
                    ui.label(f'低: {stats["priority_distribution"]["low"]}').classes(f'text-xs {low_color}')

    def refresh_todo_list():
        """ToDoリストを更新"""
        todo_list_container.clear()
        
        # ソートとフィルタリングオプションを取得
        sort_value = sort_select.value
        show_completed = show_completed_toggle.value
        
        # ソートオプションを解析
        try:
            sort_by, sort_order = sort_value.rsplit('_', 1)
        except Exception as e:
            print(f"Sort parsing error: {e}")
            sort_by = 'created_at'
            sort_order = 'desc'
        
        # ToDoリストを取得
        todos = backend.todo_service.list_todos(
            show_completed=show_completed,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 統計情報を更新
        refresh_todo_stats()
        
        with todo_list_container:
            if not todos:
                ui.label('ToDoがありません').classes('text-[10px] text-slate-500 italic p-2')
            else:
                for todo in todos:
                    # 優先度に応じた色を設定
                    priority_colors = {
                        'high': 'border-red-500 bg-red-500/10',
                        'medium': 'border-yellow-500 bg-yellow-500/10',
                        'low': 'border-blue-500 bg-blue-500/10'
                    }
                    priority_color = priority_colors.get(todo.get('priority', 'medium'), 'border-slate-500')
                    
                    # 完了状態に応じたスタイル
                    completed_style = 'opacity-50 line-through' if todo.get('completed', False) else ''
                    
                    with ui.card().classes(f'w-full p-3 border-l-4 {priority_color} {completed_style}'):
                        with ui.row().classes('w-full items-start justify-between'):
                            # 左側：ToDo内容
                            with ui.column().classes('flex-grow gap-1'):
                                # タイトル
                                title = todo.get('title', '無題')
                                title_label = ui.label(title if title else '無題').classes('text-sm font-semibold text-slate-200')
                                
                                # 説明
                                if todo.get('description'):
                                    desc = todo.get('description', '')
                                    desc_label = ui.label(desc if desc else '').classes('text-xs text-slate-400 leading-relaxed')
                                
                                # メタ情報
                                with ui.row().classes('items-center gap-3 mt-1'):
                                    # 優先度
                                    priority_labels = {
                                        'high': '高',
                                        'medium': '中',
                                        'low': '低'
                                    }
                                    priority_label = priority_labels.get(todo.get('priority', 'medium'), '中')
                                    priority_colors_classes = {
                                        'high': 'text-red-400',
                                        'medium': 'text-yellow-400',
                                        'low': 'text-blue-400'
                                    }
                                    priority_color_class = priority_colors_classes.get(todo.get('priority', 'medium'), 'text-slate-400')
                                    ui.label(f'優先度: {priority_label}').classes(f'text-xs {priority_color_class}')
                                    
                                    # 作成日時
                                    created = todo.get('created_at', '')
                                    created_label = ui.label(created[:10] if created else '').classes('text-xs text-slate-500')
                                    
                                    # 期限
                                    due_date = todo.get('due_date')
                                    if due_date:
                                        # 期限が切れているかチェック
                                        today = datetime.now().strftime('%Y-%m-%d')
                                        try:
                                            if due_date < today and not todo.get('completed', False):
                                                due_color = 'text-red-400'
                                            else:
                                                due_color = 'text-slate-400'
                                            ui.label(f'期限: {due_date}').classes(f'text-xs {due_color}')
                                        except:
                                            ui.label(f'期限: {due_date}').classes('text-xs text-slate-400')
                            
                            # 右側：操作ボタン
                            with ui.row().classes('items-center gap-1'):
                                # 完了チェックボックス
                                completed = todo.get('completed', False)
                                checkbox = ui.checkbox(
                                    value=completed,
                                    on_change=lambda e, tid=todo['id']: toggle_todo_completion(tid)
                                ).props('dense color=green-5')
                                
                                # 編集ボタン
                                ui.button(
                                    icon='edit',
                                    on_click=lambda e, tid=todo['id']: show_edit_todo_dialog(tid)
                                ).props('flat dense mini color=slate-400 size=xs')
                                
                                # 削除ボタン
                                ui.button(
                                    icon='delete',
                                    on_click=lambda e, tid=todo['id']: delete_todo(tid)
                                ).props('flat dense mini color=red-400 size=xs')

    def show_add_todo_dialog():
        """ToDo追加ダイアログを表示"""
        with ui.dialog() as dialog, ui.card().classes('w-[90vw] max-w-md'):
            ui.label('新しいToDoを追加').classes('text-lg font-bold mb-4')
            
            # フォーム
            with ui.column().classes('w-full gap-3'):
                # タイトル
                title_input = ui.input('タイトル', placeholder='ToDoのタイトルを入力').classes('w-full')
                
                # 説明
                desc_input = ui.textarea('説明', placeholder='詳細な説明（任意）').classes('w-full h-20')
                
                # 優先度
                priority_select = ui.select(
                    options={'high': '高', 'medium': '中', 'low': '低'},
                    value='medium',
                    label='優先度'
                ).classes('w-full')
                
                # 期限
                due_date_input = ui.input(
                    '期限',
                    placeholder='YYYY-MM-DD（例: 2024-12-31）'
                ).props('dense outlined').classes('w-full')
            
            # ボタン
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('キャンセル', on_click=dialog.close).props('flat')
                ui.button('追加', on_click=lambda: add_todo(
                    title=title_input.value,
                    description=desc_input.value,
                    priority=priority_select.value,
                    due_date=due_date_input.value,
                    dialog=dialog
                )).props('flat color=primary')
        
        dialog.open()

    def show_edit_todo_dialog(todo_id):
        """ToDo編集ダイアログを表示"""
        todo = backend.todo_service.load_todo(todo_id)
        if not todo:
            ui.notify('ToDoが見つかりません', color='negative')
            return
        
        with ui.dialog() as dialog, ui.card().classes('w-[90vw] max-w-md'):
            ui.label('ToDoを編集').classes('text-lg font-bold mb-4')
            
            # フォーム
            with ui.column().classes('w-full gap-3'):
                # タイトル
                title_input = ui.input('タイトル', value=todo.get('title', '')).classes('w-full')
                
                # 説明
                desc_input = ui.textarea('説明', value=todo.get('description', '')).classes('w-full h-20')
                
                # 優先度
                priority_select = ui.select(
                    options={'high': '高', 'medium': '中', 'low': '低'},
                    value=todo.get('priority', 'medium'),
                    label='優先度'
                ).classes('w-full')
                
                # 完了状態
                completed_checkbox = ui.checkbox(
                    label='完了',
                    value=todo.get('completed', False)
                ).classes('w-full')
                
                # 期限
                due_date_input = ui.input(
                    '期限',
                    value=todo.get('due_date', ''),
                    placeholder='YYYY-MM-DD（例: 2024-12-31）'
                ).props('dense outlined').classes('w-full')
            
            # ボタン
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('キャンセル', on_click=dialog.close).props('flat')
                ui.button('更新', on_click=lambda: update_todo(
                    todo_id=todo_id,
                    title=title_input.value,
                    description=desc_input.value,
                    priority=priority_select.value,
                    completed=completed_checkbox.value,
                    due_date=due_date_input.value,
                    dialog=dialog
                )).props('flat color=primary')
        
        dialog.open()

    def add_todo(title, description, priority, due_date, dialog):
        """ToDoを追加"""
        if not title or not title.strip():
            ui.notify('タイトルを入力してください', color='negative')
            return
        
        # 期限の形式をチェック
        if due_date and not due_date.strip():
            due_date = None
        elif due_date:
            try:
                # 日付形式の検証
                datetime.strptime(due_date.strip(), '%Y-%m-%d')
            except ValueError:
                ui.notify('期限の形式が正しくありません（YYYY-MMDD）', color='negative')
                return
        
        # ToDoを追加
        todo = backend.todo_service.add_todo(
            title=title.strip(),
            description=description.strip(),
            priority=priority,
            due_date=due_date.strip() if due_date else None
        )
        
        ui.notify('ToDoを追加しました', color='positive')
        dialog.close()
        refresh_todo_list()

    def update_todo(todo_id, title, description, priority, completed, due_date, dialog):
        """ToDoを更新"""
        if not title or not title.strip():
            ui.notify('タイトルを入力してください', color='negative')
            return
        
        # 期限の形式をチェック
        if due_date and not due_date.strip():
            due_date = None
        elif due_date:
            try:
                # 日付形式の検証
                datetime.strptime(due_date.strip(), '%Y-%m-%d')
            except ValueError:
                ui.notify('期限の形式が正しくありません（YYYY-MMDD）', color='negative')
                return
        
        # ToDoを更新
        updated = backend.todo_service.update_todo(
            todo_id=todo_id,
            title=title.strip(),
            description=description.strip(),
            priority=priority,
            completed=completed,
            due_date=due_date.strip() if due_date else None
        )
        
        if updated:
            ui.notify('ToDoを更新しました', color='positive')
            dialog.close()
            refresh_todo_list()
        else:
            ui.notify('更新に失敗しました', color='negative')

    def toggle_todo_completion(todo_id):
        """ToDoの完了状態を切り替え"""
        updated = backend.todo_service.toggle_todo_completion(todo_id)
        if updated:
            refresh_todo_list()
            ui.notify('状態を更新しました', color='positive')
        else:
            ui.notify('更新に失敗しました', color='negative')

    def delete_todo(todo_id):
        """ToDoを削除"""
        if ui.confirm('このToDoを削除しますか？'):
            success = backend.todo_service.delete_todo(todo_id)
            if success:
                ui.notify('ToDoを削除しました', color='positive')
                refresh_todo_list()
            else:
                ui.notify('削除に失敗しました', color='negative')

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
        if backend.stats["is_rebuilding"]: return
        
        # 通知の開始 (スピナー付き)
        n = ui.notification('Rebuilding Vector DB...', spinner=True, infinite=True, position='top-right')
        
        # ボタンをアニメーション状態に変更
        rebuild_btn.classes(add='rebuild-active text-yellow-400 border-yellow-400 bg-yellow-900/20')
        rebuild_btn.classes(remove='border-slate-800')
        rebuild_btn.set_text('BUILDING...')
        
        try:
            # バックグラウンドで再構築を実行
            success, msg = await backend.rebuild_db()
            
            # 通知の更新
            n.dismiss()
            if success:
                ui.notify('Rebuild successful!', color='positive', position='top-right', icon='check_circle')
            else:
                ui.notify(f'Rebuild failed: {msg}', color='negative', position='top-right', icon='error')
        except Exception as e:
            n.dismiss()
            ui.notify(f'System Error: {e}', color='negative', position='top-right')
        finally:
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