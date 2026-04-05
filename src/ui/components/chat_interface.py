"""チャットインターフェースUIコンポーネント"""

import json
from typing import Any, Callable, Dict, List, Optional

from nicegui import ui, app

from src.core.backend import RAGBackend
from src.ui.components.gap_analysis import render_gap_analysis
from src.ui.components.preview_dialog import create_preview_dialog

# JSONカード用インラインスタイル
JSON_CARD_CSS = '''
.json-card-container {
    margin-top: 12px;
    width: 100%;
}
.json-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-left: 4px solid #818cf8;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
    font-family: "JetBrains Mono", monospace;
}
.json-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
}
.json-card-key {
    color: #94a3b8;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
}
.json-card-value {
    color: #e2e8f0;
    font-size: 12px;
    white-space: pre-wrap;
    word-break: break-word;
    background: #0f172a;
    padding: 8px;
    border-radius: 4px;
}
.json-card-toggle {
    cursor: pointer;
    color: #818cf8;
    font-size: 11px;
}
'''


def create_chat_interface(
    backend: RAGBackend,
    session: Dict[str, Any],
    state: Dict[str, Any],
    preview_open: Optional[Callable] = None,
) -> ui.column:
    """チャットインターフェースを作成する.

    Args:
        backend: RAGBackendインスタンス
        session: チャットセッション
        state: 検索状態
        preview_open: ファイルプレビューを開くコールバック

    Returns:
        チャットインターフェースのコンテナ

    """
    # 初期化: セッション履歴をバックエンドのステートに反映
    if not backend.stats.get('chat_history'):
        backend.stats['chat_history'] = session.get('history', [])

    with ui.column().classes('w-full h-full p-4 gap-4') as container:
        # チャットメッセージ表示エリア (Refreshable)
        chat_results_container = ui.column().classes('w-full flex-grow overflow-y-auto gap-2 p-2 text-white')
        
        @ui.refreshable
        def render_messages():
            chat_results_container.clear()
            _render_chat_history(chat_results_container, backend.stats.get('chat_history', []), backend, preview_open)

        render_messages()

        # 履歴の変更を監視して再描画するタイマー
        last_history_len = [len(backend.stats.get('chat_history', []))]
        def check_history():
            current_len = len(backend.stats.get('chat_history', []))
            if current_len != last_history_len[0]:
                last_history_len[0] = current_len
                render_messages.refresh()
        
        ui.timer(1.0, check_history)

        # 入力エリア
        with ui.row().classes('w-full items-center gap-2'):
            input_field = ui.input(placeholder='メッセージを入力...').classes('flex-grow')
            input_field.bind_enabled_from(backend.stats, 'is_chat_generating', backward=lambda x: not x)
            
            send_button = ui.button('送信', icon='send', on_click=lambda: _handle_query(
                session, input_field, chat_results_container, state, backend, preview_open
            )).props('unelevated color=indigo')
            send_button.bind_enabled_from(backend.stats, 'is_chat_generating', backward=lambda x: not x)
            
            # 生成中スピナー
            with ui.row().classes('items-center').bind_visibility_from(backend.stats, 'is_chat_generating'):
                ui.spinner(size='sm').props('color=indigo')
                ui.label('Thinking...').classes('text-xs text-indigo-400')

    return container


def _handle_query(
    session: Dict[str, Any],
    input_field: ui.input,
    chat_results: ui.column,
    state: Dict[str, Any],
    backend: RAGBackend,
    preview_open: Optional[Callable] = None,
) -> None:
    """クエリを処理する (ステート更新版)."""
    query = input_field.value.strip()
    if not query or backend.stats.get('is_chat_generating'):
        return

    input_field.value = ''

    # 状態更新: ユーザーメッセージを追加
    backend.stats['chat_history'].append({"role": "user", "content": query})
    backend.stats['is_chat_generating'] = True

    # 検索とコンテキスト準備
    retriever = backend.get_retriever()
    if not retriever:
        backend.stats['chat_history'].append({"role": "ai", "content": "Database not loaded."})
        backend.stats['is_chat_generating'] = False
        return

    # 検索
    docs = retriever.invoke(query)
    state['hit_counts'] = [d.metadata['source'] for d in docs]
    
    chat_service = backend.get_chat_service()
    unique_hits = chat_service.process_search_results(docs)
    context = chat_service.format_context(docs)

    # 非同期生成を開始 (NiceGUIの非同期タスクとして実行)
    ui.timer(0.1, lambda: app.background_tasks.create(_generate_response_async(
        query, context, None, None, session, chat_results, backend, unique_hits, preview_open
    )), once=True)


async def _generate_response_async(
    query: str,
    context: str,
    md: Any,             # 旧設計互換（未使用）
    source_row: Any,     # 旧設計互換（未使用）
    session: Dict[str, Any],
    chat_results: Any,   # 旧設計互換（未使用）
    backend: RAGBackend,
    unique_hits: List[tuple],
    preview_open: Optional[Callable] = None,
) -> None:
    """非同期で応答を生成し、ステートを更新する."""
    try:
        chat_service = backend.get_chat_service()
        llm_response = await chat_service.generate_response(query, context, backend.mode)

        full = llm_response['content']
        gaps = llm_response.get('gaps', [])
        json_data = llm_response.get('json_data')

        # 履歴 (stats) に追加して保存
        ai_message = {
            "role": "ai", 
            "content": full, 
            "sources": unique_hits, 
            "gaps": gaps,
            "json_data": json_data
        }
        backend.stats['chat_history'].append(ai_message)
        
        # 従来のセッション同期も維持
        session['history'] = backend.stats['chat_history']
        title = query[:20] + ("..." if len(query) > 20 else "")
        backend.save_chat(session['id'], session['history'], title if len(session['history']) <= 2 else None)
        
    finally:
        backend.stats['is_chat_generating'] = False


def _render_chat_history(
    container: ui.column,
    history: List[Dict[str, Any]],
    backend: Optional[RAGBackend] = None,
    preview_open: Optional[Callable] = None,
) -> None:
    """チャット履歴を表示する.

    Args:
        container: コンテナ
        history: メッセージ履歴
        backend: RAGBackendインスタンス
        preview_open: ファイルプレビューを開くコールバック

    """
    with container:
        for msg in history:
            if msg['role'] == 'user':
                ui.label(f"Q: {msg['content']}").classes('text-indigo-300 font-bold text-sm bg-indigo-900/50 p-2 w-full border-l-4 border-indigo-400')
            else:
                ui.markdown(msg['content']).classes('text-white text-sm p-4 w-full border-b border-slate-600')

                # ソースファイルボタンを表示
                if msg.get('sources'):
                    with ui.row().classes('gap-2 mt-1'):
                        for p, t in msg['sources']:
                            if backend is not None:
                                base_dir = backend.config.paths.get_target_dir() if t == 'code' else backend.config.paths.get_doc_dir()
                                ui.button(
                                    f"📄 {p}",
                                    on_click=lambda fp=p, bd=str(base_dir): preview_open(fp, bd) if preview_open else None,
                                ).props('flat dense size=sm color=indigo-600 font-bold').classes('text-xs text-slate-700 bg-white px-3 py-1 rounded border border-indigo-200 hover:bg-indigo-50 transition-colors')
                            else:
                                ui.button(f"📄 {p}").props('flat dense size=sm color=indigo-600 font-bold').classes('text-xs text-slate-700 bg-white px-3 py-1 rounded border border-indigo-200')

                # ギャップ分析カードを表示
                if msg.get('gaps'):
                    render_gap_analysis(container, msg['gaps'])

                # JSONデータカードを表示
                if msg.get('json_data'):
                    _render_json_card_in_history(msg['json_data'])

                # コピーボタン
                with ui.row().classes('w-full justify-end items-center mb-4'):
                    ui.button('COPY MARKDOWN', icon='content_copy', on_click=lambda f=msg['content']: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(f)})')) \
                        .props('flat dense color=slate-400 size=sm').classes('opacity-50 hover:opacity-100')


def _render_json_card(json_data: Any) -> None:
    """JSONデータをカードとして表示する.

    Args:
        json_data: 表示するJSONデータ

    """
    card_id = f"json-card-{id(json_data)}"
    content_id = f"json-content-{id(json_data)}"

    with ui.element('div').classes('json-card-container'):
        with ui.element('div').classes('json-card').props(f'id={card_id}'):
            with ui.element('div').classes('json-card-header'):
                ui.label('JSON DATA').classes('json-card-key')
                ui.label('▼ 表示/非表示').classes('json-card-toggle').on('click', js_handler=f"""
                    () => {{
                        const el = document.getElementById('{content_id}');
                        if (el) {{
                            el.style.display = el.style.display === 'none' ? 'block' : 'none';
                        }}
                    }}
                """)

            # JSON文字列をフォーマット
            if isinstance(json_data, str):
                try:
                    formatted = json.dumps(json.loads(json_data), indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    formatted = json_data
            else:
                formatted = json.dumps(json_data, indent=2, ensure_ascii=False)

            with ui.element('pre').props(f'id={content_id}').classes('json-card-value'):
                ui.code(formatted)


def _render_json_card_in_history(json_data: Any) -> None:
    """チャット履歴内のJSONデータをカードとして表示する.

    Args:
        json_data: 表示するJSONデータ

    """
    import random
    uid = f"{random.randint(0, 99999)}"
    content_id = f"json-content-history-{uid}"

    with ui.element('div').classes('json-card-container'):
        with ui.element('div').classes('json-card'):
            with ui.element('div').classes('json-card-header'):
                ui.label('JSON DATA').classes('json-card-key')
                ui.label('▼ 表示/非表示').classes('json-card-toggle').on('click', js_handler=f"""
                    () => {{
                        const el = document.getElementById('{content_id}');
                        if (el) {{
                            el.style.display = el.style.display === 'none' ? 'block' : 'none';
                        }}
                    }}
                """)

            # JSON文字列をフォーマット
            if isinstance(json_data, str):
                try:
                    formatted = json.dumps(json.loads(json_data), indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    formatted = json_data
            else:
                formatted = json.dumps(json_data, indent=2, ensure_ascii=False)

            with ui.element('pre').props(f'id={content_id}').classes('json-card-value').style('display: none;'):
                ui.code(formatted)
