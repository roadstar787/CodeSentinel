"""チャットインターフェースUIコンポーネント"""

import json
import asyncio
from collections import Counter
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
        chat_results_container = ui.column().classes('w-full flex-grow overflow-y-auto gap-2 p-2 text-white').props('id=chat-results-scroll-area')
        
        @ui.refreshable
        def render_messages():
            chat_results_container.clear()
            _render_chat_history(chat_results_container, backend.stats.get('chat_history', []), backend, preview_open)

        render_messages()

        # 履歴の変更を監視して再描画するタイマー
        last_history_len = [len(backend.stats.get('chat_history', []))]
        last_streaming_content = [""]

        def check_history():
            current_len = len(backend.stats.get('chat_history', []))
            current_streaming = backend.stats.get('streaming_content', '')
            
            # 履歴の長さが変わった、またはストリーミング内容が変わった場合にリフレッシュ
            if current_len != last_history_len[0] or current_streaming != last_streaming_content[0]:
                last_history_len[0] = current_len
                last_streaming_content[0] = current_streaming
                render_messages.refresh()
                # 描画直後にスクロールを実行
                ui.timer(0.1, _scroll_to_bottom, once=True)
        
        def _scroll_to_bottom():
            """チャットエリアを最下部までスクロールする."""
            ui.run_javascript("const el = document.getElementById('chat-results-scroll-area'); if(el) el.scrollTop = el.scrollHeight;")

        # ストリーミング中は頻度を上げる (0.2s)、通常は1.0s
        ui.timer(0.2, check_history)

    # 固定フッターとしての入力エリア
    with ui.footer().classes('bg-transparent p-0'):
        with ui.row().classes('w-full max-w-4xl mx-auto p-4 bg-white border border-slate-300 items-end gap-2 shadow-lg rounded-t-xl'):
            input_field = ui.textarea(placeholder='メッセージを入力...').classes('flex-grow text-sm text-slate-900').props('borderless autogrow')
            input_field.bind_enabled_from(backend.stats, 'is_chat_generating', backward=lambda x: not x)
            
            # Enterで送信 (Shift+Enterは改行)
            input_field.on('keydown.enter', lambda e: submit_query() if not e.args['shiftKey'] else None)

            # フォーム送信時の処理 (Async)
            async def submit_query():
                if not input_field.value.strip() or backend.stats.get('is_chat_generating'):
                    return
                await _handle_query(session, input_field, chat_results_container, state, backend, preview_open)

            with ui.column().classes('items-center gap-1'):
                # 生成中スピナー
                with ui.row().classes('items-center').bind_visibility_from(backend.stats, 'is_chat_generating'):
                    ui.spinner(size='sm').props('color=indigo')
                    ui.label('Thinking...').classes('text-[10px] text-indigo-400')
                
                send_button = ui.button(icon='send', on_click=submit_query).props('flat round color=indigo-600')
                send_button.bind_enabled_from(backend.stats, 'is_chat_generating', backward=lambda x: not x)

    return container


async def _handle_query(
    session: Dict[str, Any],
    input_field: ui.input,
    chat_results: ui.column,
    state: Dict[str, Any],
    backend: RAGBackend,
    preview_open: Optional[Callable] = None,
) -> None:
    """クエリを非同期で処理する (ストリーミング版)."""
    query = input_field.value.strip()
    if not query or backend.stats.get('is_chat_generating'):
        return

    input_field.value = ''

    # 状態更新: ユーザーメッセージを追加
    backend.stats['chat_history'].append({"role": "user", "content": query})
    backend.stats['is_chat_generating'] = True
    backend.stats['streaming_content'] = ""

    # 検索とコンテキスト準備 (ブロッキング回避のため別スレッドまたはawait)
    retriever = backend.get_retriever()
    if not retriever:
        backend.stats['chat_history'].append({"role": "ai", "content": "Database not loaded."})
        backend.stats['is_chat_generating'] = False
        return

    # 検索 (非同期実行)
    import functools
    loop = asyncio.get_event_loop()
    docs = await loop.run_in_executor(None, functools.partial(retriever.invoke, query))
    
    # 統計情報の更新 (List -> Counter)
    state['hit_counts'] = Counter([d.metadata['source'] for d in docs])
    
    chat_service = backend.get_chat_service()
    unique_hits = chat_service.process_search_results(docs)
    context = chat_service.format_context(docs)

    # 回答生成の実行
    await _generate_response_async(
        query, context, session, backend, unique_hits, preview_open
    )


async def _generate_response_async(
    query: str,
    context: str,
    session: Dict[str, Any],
    backend: RAGBackend,
    unique_hits: List[tuple],
    preview_open: Optional[Callable] = None,
) -> None:
    """応答を生成し、リアルタイムでステートを更新する."""
    try:
        chat_service = backend.get_chat_service()
        
        # ストリーミング用コールバック
        def on_token(token: str):
            backend.stats['streaming_content'] += token

        llm_response = await chat_service.generate_response(
            query, 
            context, 
            backend.mode,
            on_token=on_token
        )

        full = llm_response['content']
        gaps = llm_response.get('gaps', [])
        json_data = llm_response.get('json_data')

        # 生成完了: streaming_content を履歴に昇格
        ai_message = {
            "role": "ai", 
            "content": full, 
            "sources": unique_hits, 
            "gaps": gaps,
            "json_data": json_data
        }
        backend.stats['chat_history'].append(ai_message)
        backend.stats['streaming_content'] = "" # クリア
        
        # セッション同期と保存
        session['history'] = backend.stats['chat_history']
        title = query[:20] + ("..." if len(query) > 20 else "")
        backend.save_chat(session['id'], session['history'], title if len(session['history']) <= 2 else None)
        
    except Exception as e:
        backend.stats['chat_history'].append({"role": "ai", "content": f"Error: {str(e)}"})
    finally:
        backend.stats['is_chat_generating'] = False
        backend.stats['streaming_content'] = ""


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
                # タグをマークダウン形式に変換して表示 (改行を確実に入れる)
                display_content = msg['content'].replace("<gaps>", "\n\n```json\n").replace("</gaps>", "\n```\n\n")
                display_content = display_content.replace("<json_data>", "\n\n```json\n").replace("</json_data>", "\n```\n\n")
                ui.markdown(display_content).classes('text-white text-sm p-4 w-full border-b border-slate-600')
                
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

        # ストリーミング中のコンテンツがあれば追加
        streaming_content = backend.stats.get('streaming_content', '') if backend else ''
        if streaming_content:
            # ストリーミング中もタグを置換 (改行を確実に入れる)
            display_streaming = streaming_content.replace("<gaps>", "\n\n```json\n").replace("</gaps>", "\n```\n\n")
            display_streaming = display_streaming.replace("<json_data>", "\n\n```json\n").replace("</json_data>", "\n```\n\n")
            ui.markdown(display_streaming).classes('text-white text-sm p-4 w-full border-b border-slate-600 animate-pulse')


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
