"""チャットインターフェースUIコンポーネント"""

import json
from typing import Any, Callable, Dict, List, Optional

from nicegui import ui, app

from src.core.backend import RAGBackend
from src.ui.components.gap_analysis import render_gap_analysis
from src.ui.components.preview_dialog import create_preview_dialog


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
        chat_results = ui.column().classes('w-full flex-grow overflow-y-auto gap-2 p-2')

        # 入力エリア
        with ui.row().classes('w-full items-center gap-2'):
            input_field = ui.input(placeholder='メッセージを入力...').classes('flex-grow')
            send_button = ui.button('送信', icon='send', on_click=lambda: _handle_query(
                session, input_field, chat_results, state, backend
            )).props('unelevated color=indigo')

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
        ui.label(f"Q: {query}").classes('text-indigo-600 font-bold text-sm bg-indigo-50 p-2 w-full border-l-4 border-indigo-600')
        md = ui.markdown('Thinking...').classes('text-slate-700 text-sm p-4 w-full border-b')
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

    # コピーボタン
    with chat_results:
        ui.button('COPY MARKDOWN', icon='content_copy', on_click=lambda f=full: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(f)})')) \
            .props('flat dense color=slate-400 size=sm').classes('self-end mt-[-10px] mb-4 opacity-50 hover:opacity-100')

    # 履歴に追加して保存
    session['history'].append({"role": "ai", "content": full, "sources": unique_hits})
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
                ui.label(f"Q: {msg['content']}").classes('text-indigo-600 font-bold text-sm bg-indigo-50 p-2 w-full border-l-4 border-indigo-600')
            else:
                ui.markdown(msg['content']).classes('text-slate-700 text-sm p-4 w-full border-b')
                with ui.row().classes('w-full justify-end items-center mb-4'):
                    ui.button('COPY MARKDOWN', icon='content_copy', on_click=lambda f=msg['content']: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(f)})')) \
                        .props('flat dense color=slate-400 size=sm').classes('opacity-50 hover:opacity-100')