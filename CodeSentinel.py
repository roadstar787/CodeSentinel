# 必要なライブラリをインポートします。
import os         # オペレーティングシステム機能
import sys        # システム固有のパラメータと機能
import asyncio    # 非同期プログラミング
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
from langchain_community.document_loaders import TextLoader  # テキストファイルローダー

# --- システム設定 ---
# アプリケーションの名前
APP_NAME = "Code Sentinel"
# アプリケーションのリビジョン（バージョン）
REVISION = "v1.3.3"

# RAG（Retrieval-Augmented Generation）のバックエンド処理を管理するクラス
class RAGBackend:
    # クラスの初期化
    def __init__(self):
        # ドキュメントの検索対象ディレクトリ
        self.target_dir = r"E:\sample\json"
        # FAISSインデックスの保存パス
        self.db_path = "faiss_index_code"
        # LM StudioのAPIエンドポイントURL
        self.lm_studio_url = "http://localhost:1234/v1"
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
        # コードに適したチャンク分割のパラメーターを設定（rag_web_ui準拠）
        code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            separators=["\nclass ", "\ndef ", "\nvoid ", "\nint ", "\nstatic ", "\n\n", "\n", " ", ""]
        )
        # 対象とするファイル拡張子
        extensions = {".hpp", ".h", ".cpp", ".py", ".json", ".cs"}
        try:
            path_obj = Path(self.target_dir)
            # 対象ディレクトリ内のファイルを再帰的に検索し、指定された拡張子を持つファイルのみを抽出
            files = [p for p in path_obj.rglob('*') if p.suffix in extensions and ".venv" not in p.parts and ".git" not in p.parts]
            for p in files:
                try:
                    # テキストローダーでファイルを読み込み
                    loader = TextLoader(str(p), encoding="utf-8")
                    raw = loader.load()
                    # メタデータに相対パスを追加
                    for d in raw: d.metadata["source"] = str(p.relative_to(self.target_dir))
                    # テキストをチャンクに分割し、ドキュメントリストに追加
                    docs.extend(code_splitter.split_documents(raw))
                except: 
                    # ファイル読み込みエラーはスキップ
                    continue
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
    
    # 検索状態の管理（ヒット数など）
    state = {'hit_counts': Counter()}

    # カスタムCSSスタイルをページのheadに追加します。
    ui.add_head_html('''
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            .hit-file { font-weight: bold; }
            .rebuild-active { animation: pulse 1.5s infinite; color: #fbbf24 !important; }
            @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
            /* モダンチャットUI用 */
            .chat-bubble { font-family: "Inter", sans-serif; font-size: 0.95rem; line-height: 1.7; border-radius: 1.25rem; }
            .code-preview pre, .code-preview code { font-family: "JetBrains Mono", monospace !important; font-size: 13px !important; }
        </style>
    ''')

    # --- プレビューダイアログ ---
    # ファイルの内容を表示するためのダイアログ
    with ui.dialog() as preview_dialog, ui.card().classes('w-[80vw] max-w-4xl h-[80vh]') as card:
        # プレビューダイアログのタイトル
        preview_title = ui.label('').classes('text-sm font-bold mb-2')
        # プレビューするコードを表示するスクロール可能なエリア
        with ui.scroll_area().classes('w-full flex-grow border p-4 bg-[#0d1117] code-preview'):
            # コードコンテンツを表示するためのMarkdown要素
            preview_code = ui.markdown('').classes('text-xs text-slate-300')
        # ダイアログを閉じるボタン
        ui.button('CLOSE', on_click=preview_dialog.close).props('flat').classes('ml-auto')

    # ファイルプレビューを開く関数
    def open_preview(file_path):
        # ファイルパスが指定されていなければ何もしない
        if not file_path: return
        # ターゲットディレクトリとファイルパスを結合してフルパスを作成
        full_path = Path(backend.target_dir) / file_path
        # フルパスがファイルでなければ何もしない
        if not full_path.is_file(): return
        try:
            # ファイルの内容をUTF-8で読み込み
            content = full_path.read_text(encoding='utf-8')
            # プレビュータイトルを設定
            preview_title.set_text(f"PREVIEW: {file_path}")
            # 言語指定付きでMarkdownセット (ファイル拡張子に基づいてシンタックスハイライト)
            ext = full_path.suffix[1:] or 'text'
            preview_code.set_content(f"```{ext}\n{content}\n```")
            # プレビューダイアログを開く
            preview_dialog.open()
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
            tab_set = ui.tab('SET', icon='settings')  # 設定タブ
            tab_sts = ui.tab('STS', icon='hub')  # ステータスタブ

        # タブの内容パネル
        with ui.tab_panels(tabs, value=tab_exp).classes('w-full bg-transparent p-4'):
            # エクスプローラータブの内容
            with ui.tab_panel(tab_exp):
                ui.label('EXPLORER').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
                # ファイルツリーを表示するコンテナ
                tree_container = ui.column().classes('w-full gap-0')

            # 設定タブの内容
            with ui.tab_panel(tab_set):
                ui.label('CONFIG').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
                # ターゲットディレクトリのパス入力フィールド
                path_input = ui.input('Path', value=backend.target_dir).props('dark dense outlined').classes('w-full mb-4')
                # パスを保存するボタン
                ui.button('SAVE PATH', on_click=lambda: save_settings(path_input.value)).props('flat border').classes('w-full text-xs mb-4')
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
            ui.label(APP_NAME).classes('text-lg font-black uppercase')
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
                node["children"] = [build_nodes(p, relative_to) for p in sorted(path.iterdir())
                                    if not p.name.startswith('.') and (p.is_dir() or p.suffix in {".py", ".cs", ".cpp", ".h", ".json"})]
                node["icon"] = "folder"
            else: node["icon"] = "description"
            return node
        try:
            root = Path(backend.target_dir)
            if not root.exists(): return
            tree_data = [build_nodes(root, root)]
            with tree_container:
                t = ui.tree(nodes=tree_data, label_key='label', on_select=lambda e: open_preview(e.value)).props('dark dense')
                t.add_slot('default-header', '<div :class="props.node.class" :style="props.node.style" style="border-radius: 4px; padding: 2px 6px;">{{ props.node.label }}</div>')
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
            if not retriever:
                md.set_content("Database not loaded.")
                return
            docs = await run.io_bound(retriever.invoke, query)
            hits = [d.metadata['source'] for d in docs]
            state['hit_counts'] = Counter(hits)
            refresh_explorer()
            
            unique_hits = list(set(hits))
            with source_row:
                for p in unique_hits:
                    ui.button(p, on_click=lambda e, path=p: open_preview(path)).props('outline dense size=xs').classes('text-[10px] text-indigo-500 border-indigo-200 bg-indigo-50')
            
            context = "\n".join([f"FILE: {d.metadata['source']}\n{d.page_content}" for d in docs])
            llm = ChatOpenAI(base_url=backend.lm_studio_url, api_key="lm-studio", temperature=0.1, streaming=True)
            chain = ChatPromptTemplate.from_template("回答は日本語で行ってください。\n\nContext:\n{c}\n\nQ: {i}") | llm | StrOutputParser()
            full = ""
            async for chunk in chain.astream({"c": context, "i": query}):
                full += chunk
                md.set_content(full)
                ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')
        except Exception as e:
            md.set_content(f"Error: {str(e)}")
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
        # ボタンをアニメーション状態に変更
        rebuild_btn.classes(add='rebuild-active')
        rebuild_btn.set_text('BUILDING...')
        
        # バックグラウンドで再構築を実行
        await run.io_bound(backend.rebuild_db)
        
        # アニメーション状態を解除してテキストを元に戻す
        rebuild_btn.classes(remove='rebuild-active')
        rebuild_btn.set_text('REBUILD')
        
        idx_label.set_text(f'IDX: {backend.stats["total_chunks"]}')
        refresh_explorer()

    backend.load_db()
    refresh_explorer()
    asyncio.create_task(update_status_loop())

ui.run(title=APP_NAME, storage_secret='sentinel_secret_key')
