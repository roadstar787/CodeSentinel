"""ToDoタブUIコンポーネント"""

from typing import Any, Dict, Optional

from nicegui import ui


def create_todo_tab(
    backend: Any,
) -> ui.column:
    """ToDoタブを作成する.

    Args:
        backend: RAGBackendインスタンス

    Returns:
        ToDoタブのコンテナ

    """
    todo_list_container = ui.column().classes('w-full gap-2')
    todo_stats_container = ui.row().classes('w-full gap-4 mb-4')

    _refresh_todo_list(todo_list_container, todo_stats_container, backend)

    return todo_list_container


def _refresh_todo_list(
    todo_list_container: Optional[ui.column],
    todo_stats_container: Optional[ui.row],
    backend: Any,
) -> None:
    """ToDoリストを更新."""
    _render_todo_list(todo_list_container, todo_stats_container, backend)


def _render_todo_list(
    todo_list_container: Optional[ui.column],
    todo_stats_container: Optional[ui.row],
    backend: Any,
) -> None:
    """ToDoリストを更新."""
    if todo_list_container is None:
        return

    todo_list_container.clear()
    if todo_stats_container:
        todo_stats_container.clear()

    todo_service = backend.get_todo_service() if backend else None
    if todo_service is None:
        return

    todos = todo_service.list_todos(show_completed=False)

    # 統計情報を表示
    if todo_stats_container:
        stats = todo_service.get_todo_statistics()
        with todo_stats_container:
            ui.label(f'未完了: {stats.get("pending", 0)}').classes('text-yellow-400 text-xs')
            ui.label(f'完了: {stats.get("completed", 0)}').classes('text-green-400 text-xs')

    with todo_list_container:
        if not todos:
            ui.label('ToDoがありません').classes('text-gray-400')
        else:
            for todo in todos[:20]:
                _render_todo_item(todo, todo_list_container, todo_stats_container, backend)


def _render_todo_item(
    todo: Dict[str, Any],
    list_container: ui.column,
    stats_container: Optional[ui.row],
    backend: Any,
) -> None:
    """ToDoアイテムを表示."""
    with ui.row().classes('w-full items-center p-2 rounded hover:bg-gray-700'):
        todo_id = todo.get('id', '')
        ui.checkbox(
            value=todo.get('completed', False),
            on_change=lambda e, tid=todo_id: _toggle_todo(tid, e.value, backend, list_container, stats_container)
        ).classes('text-green-400')
        ui.label(todo.get('title', '')).classes('text-white flex-1 text-sm')
        priority_color = {'high': 'red', 'medium': 'yellow', 'low': 'green'}.get(todo.get('priority', 'medium'), 'gray')
        ui.icon('circle', color=priority_color, size='xs')
        ui.button(
            icon='delete',
            on_click=lambda e, tid=todo_id: _delete_todo(tid, backend, list_container, stats_container)
        ).props('flat dense size=sm color=red-4').classes('opacity-50 hover:opacity-100')


def _toggle_todo(
    todo_id: str,
    completed: bool,
    backend: Any,
    todo_list_container: Optional[ui.column],
    todo_stats_container: Optional[ui.row],
) -> None:
    """ToDoの完了状態を切り替え."""
    todo_service = backend.get_todo_service() if backend else None
    if todo_service:
        todo_service.toggle_todo_completion(todo_id)
    _refresh_todo_list(todo_list_container, todo_stats_container, backend)


def _delete_todo(
    todo_id: str,
    backend: Any,
    todo_list_container: Optional[ui.column],
    todo_stats_container: Optional[ui.row],
) -> None:
    """ToDoを削除."""
    todo_service = backend.get_todo_service() if backend else None
    if todo_service:
        todo_service.delete_todo(todo_id)
    ui.notify('ToDoを削除しました')
    _refresh_todo_list(todo_list_container, todo_stats_container, backend)


def _add_todo(
    title: str,
    priority: Optional[str],
    backend: Any,
    dialog: Any,
    todo_list_container: Optional[ui.column],
    todo_stats_container: Optional[ui.row],
) -> None:
    """ToDoを追加."""
    if not title:
        ui.notify('タイトルを入力してください', color='warning')
        return

    todo_service = backend.get_todo_service() if backend else None
    if todo_service:
        todo_service.add_todo(title=title, priority=priority)
    ui.notify('ToDoを追加しました')
    dialog.close()
    _refresh_todo_list(todo_list_container, todo_stats_container, backend)


def show_add_todo_dialog(
    backend: Any,
    todo_list_container: Optional[ui.column] = None,
    todo_stats_container: Optional[ui.row] = None,
) -> None:
    """ToDo追加ダイアログを表示."""
    with ui.dialog() as dialog, ui.card():
        ui.label('新しいToDo').classes('text-lg font-bold')
        title_input = ui.input('タイトル').props('outlined')
        priority_select = ui.select(
            options={'high': '高', 'medium': '中', 'low': '低'},
            value='medium',
            label='優先度'
        ).props('outlined')
        with ui.row():
            ui.button(
                '追加',
                on_click=lambda: _add_todo(
                    title_input.value,
                    priority_select.value,
                    backend,
                    dialog,
                    todo_list_container,
                    todo_stats_container,
                )
            )
            ui.button('キャンセル', on_click=dialog.close)
    dialog.open()