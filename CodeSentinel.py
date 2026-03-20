import asyncio
import json
import uuid
from typing import Counter
from pathlib import Path
import psutil

from nicegui import ui, run, app
from starlette.responses import FileResponse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# 自作モジュールのインポート：ロジック、スタイル、コンポーネントを分離
from backend import RAGBackend, APP_NAME, APP_VERSION
from ui.styles import APP_CSS
from ui.layouts import create_header, create_footer
from ui.components import Explorer, PreviewDialog, render_message, render_gap_results

# バックエンドエンジンの初期化
backend = RAGBackend()

from urllib.parse import quote

@app.get('/serve_file/{file_type}/{rel_path:path}')
async def serve_file(file_type: str, rel_path: str):
    """
    ファイルを動的に配信するルート。
    """
    base_dir = backend.target_dir if file_type == 'code' else backend.doc_dir
    full_path = Path(base_dir) / rel_path
    
    # ログ出力（デバッグ用）
    print(f"Serve request: type={file_type}, rel={rel_path} -> full={full_path}")
    
    if full_path.exists() and full_path.is_file():
        # content_type 算出のために拡張子を確認
        ext = full_path.suffix.lower()
        media_type = None
        if ext == ".pdf": media_type = "application/pdf"
        elif ext == ".pptx": media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        elif ext == ".xlsx": media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return FileResponse(full_path, media_type=media_type)
    
    print(f"File not found: {full_path}")
    return {"error": f"File not found: {rel_path}"}, 404

@ui.page('/')
async def main_page():
    """
    メインページのエントリポイント。
    NiceGUIのリアクティブなUIコンポーネントを組み立て、各イベントハンドラを定義します。
    """
    # ユーザー設定(パスやモード)の読み込み
    backend.target_dir = app.storage.user.get('target_dir', backend.target_dir)
    backend.doc_dir = app.storage.user.get('doc_dir', backend.doc_dir)
    backend.mode = app.storage.user.get('mode', 'Normal')
    
    # データベースの自動ロード
    if not backend.vectorstore:
        success = await run.io_bound(backend.load_db)
        if success:
            ui.notify(f"Database loaded: {backend.stats['total_chunks']} chunks", color='positive', pos='top')
    
    # チャットセッションの状態管理
    session = {'id': app.storage.user.get('current_chat_id', str(uuid.uuid4())), 'history': []}
    chat_data = backend.load_chat(session['id'])
    if chat_data: 
        session['history'] = chat_data.get('messages', [])
        print(f"Session {session['id']} restored with {len(session['history'])} messages.")
    
    # ファイルエクスプローラー用ヒットカウント
    state = {'hit_counts': Counter()}

    # カスタムCSSの注入
    ui.add_head_html(APP_CSS)

    # プレビュー用ダイアログの初期化
    previewer = PreviewDialog()
    
    def open_preview_bridge(rel_path, base_dir, line=None, fix_code=None):
        """パスを解決してプレビューアを呼び出すためのブリッジ関数。"""
        if not rel_path: return
        # ドキュメントディレクトリかコードディレクトリかを判定
        file_type = 'document' if str(base_dir) == str(backend.doc_dir) else 'code'
        full = Path(base_dir) / rel_path
        previewer.open(full, rel_path, line, fix_code, file_type=file_type)

    # --- 左サイドバー（ドロワー）: 明示的に開いた状態(value=True)に設定 ---
    with ui.left_drawer(value=True, fixed=True).classes('p-0 bg-[#2d3748]') as drawer:
        with ui.tabs().classes('w-full text-slate-500') as tabs:
            tab_exp = ui.tab('EXP', icon='account_tree')     # ファイルエクスプローラー
            tab_cht = ui.tab('CHATS', icon='chat')           # チャット履歴
            tab_set = ui.tab('SET', icon='settings')         # 設定
            tab_sts = ui.tab('STS', icon='hub')              # システムステータス

        with ui.tab_panels(tabs, value=tab_exp).classes('w-full bg-transparent p-4'):
            # エクスプローラー画面
            with ui.tab_panel(tab_exp):
                ui.label('EXPLORER').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
                tree_container = ui.column().classes('w-full gap-0')
                explorer = Explorer(tree_container, open_preview_bridge)

            # チャット履歴一覧
            with ui.tab_panel(tab_cht):
                with ui.row().classes('w-full items-center justify-between mb-4'):
                    ui.label('HISTORY').classes('text-[10px] text-slate-600 tracking-widest')
                    ui.button(icon='add', on_click=lambda: start_new_chat()).props('flat round dense color=slate-400')
                chat_list_container = ui.column().classes('w-full gap-2')

            # パス・DB再構築設定
            with ui.tab_panel(tab_set):
                ui.label('CONFIG').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
                path_input = ui.input('Code Path', value=backend.target_dir).props('dark dense outlined').classes('w-full mb-2')
                doc_path_input = ui.input('Doc Path', value=backend.doc_dir).props('dark dense outlined').classes('w-full mb-4')
                ui.button('SAVE PATHS', on_click=lambda: save_settings(path_input.value, doc_path_input.value)).props('flat border').classes('w-full text-xs mb-4')
                rebuild_btn = ui.button('REBUILD', on_click=lambda: rebuild_task()).props('flat icon=refresh').classes('w-full border border-slate-800 text-xs')

            # システム負荷・接続状況
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
                    chunk_count_label = ui.label(str(backend.stats["total_chunks"])).classes('status-value')
                with ui.element('div').classes('status-item'):
                    ui.label('Last Build').classes('status-label')
                    last_update_label = ui.label(backend.stats["last_rebuild"]).classes('status-value')

                ui.separator().classes('bg-slate-700 my-6 opacity-30')
                ui.label('SYSTEM LOAD').classes('text-[10px] font-bold text-indigo-400 mb-4 tracking-widest')
                with ui.element('div').classes('status-item'):
                    ui.label('LM Studio').classes('status-label')
                    with ui.row().classes('items-center gap-2'):
                        lm_indicator = ui.icon('circle', color='grey').classes('text-[10px]')
                        lm_status_text = ui.label('Checking...').classes('status-value')
                with ui.element('div').classes('status-item'):
                    ui.label('Active Model').classes('status-label')
                    lm_model_label = ui.label('N/A').classes('status-value truncate max-w-[120px]')
                with ui.element('div').classes('status-item'):
                    ui.label('CPU').classes('status-label')
                    cpu_label = ui.label('0%').classes('status-value')
                with ui.element('div').classes('status-item'):
                    ui.label('RAM').classes('status-label')
                    ram_label = ui.label('0GB').classes('status-value')

        ui.button('SHUTDOWN', on_click=app.shutdown).props('flat icon=power_settings_new color=red-4').classes('w-full mt-auto mb-4 px-4')

    # --- コンテンツ本体と入力バー ---
    create_header(drawer.toggle, APP_NAME, APP_VERSION, {"mode": backend.mode, "total_chunks": backend.stats["total_chunks"]}, lambda v: change_mode(v))
    chat_results = ui.column().classes('w-full max-w-4xl mx-auto p-8 pb-40 gap-4')
    input_field = create_footer(lambda: handle_query())

    # --- ユーザーアクション用コールバック群 ---

    def save_settings(v_target, v_doc):
        """パス設定を保存し、エクスプローラーをリフレッシュします。"""
        app.storage.user['target_dir'] = v_target
        app.storage.user['doc_dir'] = v_doc
        backend.target_dir = v_target
        backend.doc_dir = v_doc
        explorer.refresh(backend.target_dir, backend.doc_dir, state['hit_counts'])

    def change_mode(v):
        """動作モード(Q&A/GAP)を切り替えます。"""
        app.storage.user['mode'] = v
        backend.mode = v
        ui.notify(f"Mode changed to: {v}")

    async def update_status_loop():
        """CPU/RAM使用率およびLM Studio接続状況を定期的に監視・更新します。"""
        while True:
            cpu_label.set_text(f"{psutil.cpu_percent()}%")
            mem = psutil.virtual_memory()
            ram_label.set_text(f"{mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB")
            connected = await backend.check_lm_studio()
            lm_indicator.props(f'color={"green" if connected else "red"}')
            lm_status_text.set_text(f'{"ONLINE" if connected else "OFFLINE"}')
            lm_model_label.set_text(backend.stats["model"])
            is_loaded = backend.vectorstore is not None
            status_chip.set_text('ONLINE' if is_loaded else 'OFFLINE')
            status_chip.classes(replace='bg-green-900/40 text-green-400' if is_loaded else 'bg-red-900/40 text-red-400')
            chunk_count_label.set_text(str(backend.stats["total_chunks"]))
            last_update_label.set_text(backend.stats["last_rebuild"])
            await asyncio.sleep(3)

    async def handle_query():
        """
        ユーザーの入力を処理し、RAG検索を実行してAIから回答を取得します。
        ストリーミング表示に対応しています。
        """
        query = input_field.value.strip()
        if not query: return
        input_field.value = ''
        session['history'].append({"role": "user", "content": query})

        with chat_results:
            render_message(chat_results, 'user', query)
            # ローディング表示
            md = ui.markdown('Thinking...').classes('text-slate-700 text-sm p-4 w-full border-b')
            source_row = ui.row().classes('gap-2 mt-1')

        try:
            # RAG検索の実行
            retriever = backend.get_retriever()
            if not retriever:
                md.set_content("Database not loaded.")
                return
            docs = await run.io_bound(retriever.invoke, query)
            
            # エクスプローラーのハイライトを更新
            hits = [d.metadata['source'] for d in docs]
            state['hit_counts'] = Counter(hits)
            explorer.refresh(backend.target_dir, backend.doc_dir, state['hit_counts'])
            
            unique_hits = []
            seen = set()
            for d in docs:
                pair = (d.metadata['source'], d.metadata.get('type', 'code'))
                if pair not in seen:
                    unique_hits.append(pair)
                    seen.add(pair)

            # 引用元リンクの描画
            with source_row:
                for p, t in unique_hits:
                    b_dir = backend.target_dir if t == 'code' else backend.doc_dir
                    ui.button(p, on_click=lambda e, path=p, bd=b_dir: open_preview_bridge(path, bd)).props('outline dense size=xs').classes('text-[10px] text-indigo-500 border-indigo-200 bg-indigo-50')
            
            # コンテキスト構築
            context = "\n".join([f"TYPE: {d.metadata.get('type','unknown')}\nFILE: {d.metadata['source']}\n{d.page_content}" for d in docs])
            llm = ChatOpenAI(
                base_url=backend.lm_studio_url, 
                api_key="lm-studio", 
                temperature=0.1, 
                streaming=True,
                max_tokens=8192  # トークン不足による途切れを防ぐため大幅に引き上げ
            )
            
            # プロンプトの構築（モードに応じて変更）
            prompt_str = """あなたは優秀なソフトウェアエンジニア兼テクニカルドキュメントアナリストです。
提供されたコンテキストに基づいて、仕様書(document)とソースコード(code)を詳細に比較・分析してください。

Q: {i}

【回答ガイドライン】
1. 仕様書(document)とソースコード(code)を網羅的に比較・分析してください。
2. 仕様にあるが実装されていない項目、または矛盾・乖離している箇所を特定してください。
3. **まず、分析結果の要約（どのファイルにどのような乖離があるか）を日本語の文章で分かりやすく記述してください。**
4. **【重要】修正後のソースコードは本文（文章部分）には絶対に含めないでください。** すべて以下の JSON 内の "corrected_code" フィールドにのみ記述してください。

【出力形式：構造化データ】
分析結果の要約のあとに、見つかった **すべての** 乖離・矛盾項目を漏れなく JSON 形式で `<gaps>` タグ内に含めてください。
注意：分析結果（本文）で言及したすべての項目に対応するカードを必ず出力してください。
トークン制限を考慮し、 "corrected_code" は修正箇所のスニペットでも構いません。網羅性を最優先してください。

形式:
<gaps>
[ {{"file": "ファイル名", "line": 行番号またはnull, "issue": "乖離・矛盾の内容", "corrected_code": "修正後のコード（スニペット可）"}} ]
</gaps>

Context:
{c}
""" if backend.mode == 'Gap' else "回答は日本語で行ってください。\n\nContext:\n{c}\n\nQ: {i}"

            chain = ChatPromptTemplate.from_template(prompt_str) | llm | StrOutputParser()
            full = ""
            # ストリーミング逐次表示
            async for chunk in chain.astream({"c": context, "i": query}):
                full += chunk
                display_text = full.split("<gaps>")[0] if "<gaps>" in full else full
                md.set_content(display_text)
                ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')
            
            # Gap分析モードならカードを描画
            if backend.mode == 'Gap':
                render_gap_results(chat_results, full, open_preview_bridge, backend.target_dir, sources=unique_hits)

            with chat_results:
                ui.button('COPY MARKDOWN', icon='content_copy', on_click=lambda f=full: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(f)})')) \
                    .props('flat dense color=slate-400 size=sm').classes('self-end mt-[-10px] mb-4 opacity-50 hover:opacity-100')
            
            # 履歴の保存
            session['history'].append({"role": "ai", "content": full, "sources": unique_hits})
            title = query[:20] + ("..." if len(query) > 20 else "")
            backend.save_chat(session['id'], session['history'], title if len(session['history']) <= 2 else None)
            refresh_chat_list()

        except Exception as e:
            md.set_content(f"Error: {str(e)}")

    def refresh_chat_list():
        """チャット履歴の一覧をサイドバーに再描画します。"""
        chat_list_container.clear()
        for c in backend.list_chats():
            with chat_list_container, ui.row().classes('w-full items-center gap-1 group'):
                btn = ui.button(on_click=lambda e, cid=c['id']: load_chat_session(cid)).props('flat no-caps dense').classes('flex-grow text-left justify-start px-2 py-1 rounded hover:bg-slate-700/50')
                with btn, ui.column().classes('gap-0'):
                    ui.label(c['title']).classes('text-xs text-slate-200 line-clamp-1')
                    ui.label(c['date']).classes('text-[9px] text-slate-500')
                ui.button(icon='delete', on_click=lambda e, cid=c['id']: delete_chat_session(cid)).props('flat round dense size=sm color=red-4').classes('opacity-0 group-hover:opacity-100 transition-opacity')

    def load_chat_session(chat_id):
        """過去のチャットセッションを選択してロードします。"""
        data = backend.load_chat(chat_id)
        if not data: return
        session.update({'id': chat_id, 'history': data.get('messages', [])})
        app.storage.user['current_chat_id'] = chat_id
        chat_results.clear()
        for msg in session['history']:
            render_message(chat_results, msg['role'], msg['content'], msg.get('sources'), open_preview_bridge, backend.target_dir, backend.doc_dir)
        ui.notify(f"Chat loaded: {data['title']}")
        refresh_chat_list()

    def start_new_chat():
        """現在のセッションをリセットし、新しいチャットを開始します。"""
        new_id = str(uuid.uuid4())
        session.update({'id': new_id, 'history': []})
        app.storage.user['current_chat_id'] = new_id
        chat_results.clear()
        ui.notify("New chat started")
        refresh_chat_list()

    def delete_chat_session(chat_id):
        """チャット履歴ファイルを削除します。"""
        backend.delete_chat(chat_id)
        if session['id'] == chat_id: start_new_chat()
        else: refresh_chat_list()
        ui.notify("Chat deleted")

    async def rebuild_task():
        """バックグラウンドでベクターストアを再構築します。"""
        if backend.stats["is_rebuilding"]: return
        n = ui.notification('Rebuilding Vector DB...', spinner=True, infinite=True, position='top-right')
        rebuild_btn.classes(add='rebuild-active text-yellow-400 border-yellow-400 bg-yellow-900/20').set_text('BUILDING...')
        try:
            success, msg = await run.io_bound(backend.rebuild_db)
            n.dismiss()
            ui.notify('Rebuild successful!' if success else f'Rebuild failed: {msg}', color='positive' if success else 'negative')
        finally:
            rebuild_btn.classes(remove='rebuild-active text-yellow-400 border-yellow-400 bg-yellow-900/20').set_text('REBUILD')

    # 初期起動時のリフレッシュ
    asyncio.create_task(update_status_loop())
    explorer.refresh(backend.target_dir, backend.doc_dir, state['hit_counts'])
    refresh_chat_list()
    
    # 保存されている履歴がある場合は描画
    if session['history']:
        for msg in session['history']:
            render_message(chat_results, msg['role'], msg['content'], msg.get('sources'), open_preview_bridge, backend.target_dir, backend.doc_dir)

# --- GUIアプリの起動 ---
if __name__ in {"__main__", "__mp_main__"}:
    # 秘密鍵を設定してstorage（永続化機能）を有効化
    ui.run(title=APP_NAME, port=8080, storage_secret='codesentinel_secret')
