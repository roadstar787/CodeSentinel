"""チャット履歴タブUIコンポーネント"""

import uuid
from typing import Any, Dict, List, Optional

from nicegui import ui, app

def create_chat_history_tab(
    backend: Any,
    session: Dict[str, Any],
    state: Dict[str, Any],
) -> ui.column:
    """チャット履歴タブを作成する.

    Args:
        backend: RAGBackendインスタンス
        session: チャットセッション
        state: 検索状態

    Returns:
        チャット履歴タブのコンテナ

    """
    chat_list_container = ui.column().classes('w-full gap-2')
    _render_chat_list(chat_list_container, backend, session)

    return chat_list_container


def _render_chat_list(
    container: Optional[ui.column],
    backend: Any,
    session: Optional[Dict[str, Any]] = None,
) -> None:
    """チャット一覧を表示."""
    if container is None:
        return

    container.clear()
    if session is None:
        session = {'id': '', 'history': []}

    with container:
        with ui.row().classes('w-full items-center justify-between mb-4'):
            ui.label('HISTORY').classes('text-[10px] text-slate-600 tracking-widest')
            ui.button(
                icon='add',
                on_click=lambda: _start_new_chat(backend, session, container)
            ).props('flat round dense color=slate-400')

        chats = backend.list_chats() if backend else []
        if not chats:
            ui.label('チャット履歴がありません').classes('text-gray-400')
        else:
            for chat in chats[:10]:
                chat_id = chat.get('id', '')
                with ui.row().classes('w-full items-start cursor-pointer hover:bg-gray-800/50 p-2 rounded gap-3'):
                    ui.icon('chat', size='18px').classes('text-indigo-400 mt-1')
                    
                    with ui.column().classes('flex-1 gap-0 cursor-pointer').on('click', lambda e, cid=chat_id: _load_chat(cid, backend, session, container)):
                        ui.label(chat.get('title', 'Untitled')).classes('text-slate-200 text-sm font-medium leading-tight line-clamp-1')
                        ui.label(chat.get('date', '')).classes('text-slate-500 text-[10px]')

                    ui.button(
                        icon='delete',
                        on_click=lambda e, cid=chat_id: _delete_chat(cid, backend, session, container)
                    ).props('flat dense size=sm color=red-4').classes('opacity-30 hover:opacity-100 mt-0.5')


def _load_chat(
    chat_id: str,
    backend: Any,
    session: Optional[Dict],
    container: ui.column,
) -> None:
    """チャットをロード (ステート連動版)."""
    chat_data = backend.load_chat(chat_id) if backend else None
    if chat_data and session:
        session['id'] = chat_id
        session['history'] = chat_data.get('messages', [])
        
        # バックエンドのステート（真のソース）を更新
        if backend:
            backend.stats['chat_history'] = session['history']
            
        ui.notify(f'チャット "{chat_data.get("title", "Untitled")}" をロードしました')
        try:
            app.storage.user['current_chat_id'] = chat_id
        except RuntimeError:
            pass
            
    _render_chat_list(container, backend, session)


def _delete_chat(
    chat_id: str,
    backend: Any,
    session: Optional[Dict],
    container: ui.column,
) -> None:
    """チャットを削除."""
    if backend:
        backend.delete_chat(chat_id)
    ui.notify('チャットを削除しました')
    if session and session.get('id') == chat_id:
        session['id'] = str(uuid.uuid4())
        session['history'] = []
        if backend:
            backend.stats['chat_history'] = []
    _render_chat_list(container, backend, session)


def _start_new_chat(
    backend: Any,
    session: Optional[Dict[str, Any]] = None,
    chat_list_container: Optional[ui.column] = None,
) -> None:
    """新しいチャットを開始."""
    if session is None:
        session = {'id': '', 'history': []}
    session['id'] = str(uuid.uuid4())
    session['history'] = []
    
    if backend:
        backend.stats['chat_history'] = []
    
    ui.notify('新しいチャットを開始しました')
    _render_chat_list(chat_list_container, backend, session)