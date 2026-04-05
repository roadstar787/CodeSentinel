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
    state: Dict[str, Any]
) -> ui.column:
    """チャットインターフェースを作成する.

    Args:
        backend: RAGBackendインスタンス
        session: チャットセッション
        state: 検索状態

    Returns:
        チャットインターフェースのコンテナ

    """
    with ui.column().classes('w-full h-full p-4 gap-4') as container:
        # チャットメッセージ表示エリア
        chat_results = ui.column().classes('w-full flex-grow overflow-y-auto gap-2 p-2 text-white')

        # 入力エリア
        with ui.row().classes('w-full items-center gap-2'):
            input_field = ui.input(placeholder='メッセージを入力...').classes('flex-grow')
            send_button = ui.button('送信', icon='send', on_click=lambda: _handle_query(
                session, input_field, chat_results, state, backend
            )).props('unelevated color=indigo')

    # JSONカード用CSSを追加
    ui.add_head_html(f'<style>{JSON_CARD_CSS}</style>')

    # 初期メッセージを表示
    _render_chat_history(chat_results, session['history'])

    return container


def _handle_query(
    session: Dict[str, Any],
    input_field: ui.input,
    chat_results: ui.column,
    state: Dict[str, Any],
    backend: RAGBackend
) -> None:
    """クエリを処理する.

    Args:
        session: チャットセッション
        input_field: 入力フィールド
        chat_results: チャット結果コンテナ
        state: 検索状態
        backend: RAGBackendインスタンス

    """
    query = input_field.value.strip()
    if not query:
        return

    input_field.value = ''

    # 履歴に追加
    session['history'].append({"role": "user", "content": query})

    # ユーザーメッセージを表示
    with chat_results:
        ui.label(f"Q: {query}").classes('text-indigo-300 font-bold text-sm bg-indigo-900/50 p-2 w-full border-l-4 border-indigo-400')
        md = ui.markdown('Thinking...').classes('text-white text-sm p-4 w-full border-b border-slate-600')
        source_row = ui.row().classes('gap-2 mt-1')

    # 検索と応答生成
    retriever = backend.get_retriever()
    if not retriever:
        md.set_content("Database not loaded.")
        return

    # 同期的に検索を実行
    docs = retriever.invoke(query)
    hits = [d.metadata['source'] for d in docs]
    state['hit_counts'] = hits

    # コンテキストをフォーマット
    chat_service = backend.get_chat_service()
    unique_hits = chat_service.process_search_results(docs)
    context = chat_service.format_context(docs)

    # 応答を生成（同期的に実行）
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 既にイベントループが実行中の場合は新しいタスクとしてスケジュール
            asyncio.create_task(_generate_response_async(
                query, context, md, source_row, session, chat_results, backend, unique_hits
            ))
        else:
            loop.run_until_complete(_generate_response_async(
                query, context, md, source_row, session, chat_results, backend, unique_hits
            ))
    except RuntimeError:
        # イベントループがない場合は新しいループを作成
        asyncio.run(_generate_response_async(
            query, context, md, source_row, session, chat_results, backend, unique_hits
        ))


async def _generate_response_async(
    query: str,
    context: str,
    md: ui.markdown,
    source_row: ui.row,
    session: Dict[str, Any],
    chat_results: ui.column,
    backend: RAGBackend,
    unique_hits: List[tuple]
) -> None:
    """非同期で応答を生成する."""
    chat_service = backend.get_chat_service()
    llm_response = await chat_service.generate_response(query, context, backend.mode)

    full = llm_response['content']
    md.set_content(full)

    # ソースを表示
    with source_row:
        for p, t in unique_hits:
            ui.button(f"📄 {p}").props('flat dense size=sm color=indigo-400 font-bold').classes('text-[10px] bg-indigo-50/50 px-2 rounded border border-indigo-100/50')

    # ギャップ分析カードを表示（Gapモードの場合）
    gaps = llm_response.get('gaps', [])
    if gaps:
        render_gap_analysis(chat_results, gaps)

    # JSONデータをカードとして表示（メタデータがある場合）
    json_data = llm_response.get('json_data')
    if json_data:
        with chat_results:
            _render_json_card(json_data)

    # コピーボタン
    with chat_results:
        ui.button('COPY MARKDOWN', icon='content_copy', on_click=lambda f=full: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(f)})')) \
            .props('flat dense color=slate-400 size=sm').classes('self-end mt-[-10px] mb-4 opacity-50 hover:opacity-100')

    # 履歴に追加して保存
    session['history'].append({"role": "ai", "content": full, "sources": unique_hits, "gaps": gaps})
    title = query[:20] + ("..." if len(query) > 20 else "")
    backend.save_chat(session['id'], session['history'], title if len(session['history']) <= 2 else None)


def _render_chat_history(container: ui.column, history: List[Dict[str, Any]]) -> None:
    """チャット履歴を表示する.

    Args:
        container: コンテナ
        history: メッセージ履歴

    """
    with container:
        for msg in history:
            if msg['role'] == 'user':
                ui.label(f"Q: {msg['content']}").classes('text-indigo-300 font-bold text-sm bg-indigo-900/50 p-2 w-full border-l-4 border-indigo-400')
            else:
                ui.markdown(msg['content']).classes('text-white text-sm p-4 w-full border-b border-slate-600')

                # ソースを表示
                if msg.get('sources'):
                    with ui.row().classes('gap-2 mt-1'):
                        for p, t in msg['sources']:
                            ui.button(f"📄 {p}").props('flat dense size=sm color=indigo-400 font-bold').classes('text-[10px] bg-indigo-50/50 px-2 rounded border border-indigo-100/50')

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
