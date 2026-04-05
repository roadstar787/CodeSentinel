"""ToDo管理UIコンポーネント"""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from nicegui import ui

from src.core.backend import RAGBackend


def create_todo_manager(
    backend: RAGBackend,
) -> ui.column:
    """ToDo管理コンポーネントを作成する.

    Args:
        backend: RAGBackendインスタンス

    Returns:
        ToDo管理のコンテナ

    """
    with ui.column().classes('w-full h-full p-4 gap-4') as container:
        ui.label('ToDo管理').classes('text-white text-lg font-bold')

        # 統計情報コンテナ
        stats_container = ui.column().classes('w-full gap-2')
        _refresh_todo_stats(stats_container, backend)

        # ToDo一覧コンテナ
        todo_list_container = ui.column().classes('w-full flex-grow overflow-y-auto')
        _render_todo_list(todo_list_container, stats_container, backend)

        # 追加ボタン
        with ui.row().classes('w-full justify-end'):
            ui.button('追加', icon='add', on_click=lambda: _show_add_todo_dialog(backend, todo_list_container, stats_container)).props('unelevated color=indigo')

    return container


def _render_todo_list(
    container: ui.column,
    stats_container: ui.column,
    backend: RAGBackend,
) -> None:
    """ToDo一覧を表示する.

    Args:
        container: コンテナ
        stats_container: 統計情報コンテナ
        backend: RAGBackendインスタンス

    """
    container.clear()
    todo_service = backend.get_todo_service()
    todos = todo_service.list_todos(show_completed=False)

    with container:
        if not todos:
            ui.label('ToDoがありません').classes('text-gray-400 text-sm p-4')
        else:
            for todo in todos[:20]:  # 最大20件まで表示
                _render_todo_item(todo, container, stats_container, backend)


def _render_todo_item(
    todo: Dict[str, Any],
    container: ui.column,
    stats_container: ui.column,
    backend: RAGBackend,
) -> None:
    """ToDoアイテムを表示する.

    Args:
        todo: ToDoデータ
        container: コンテナ
        stats_container: 統計情報コンテナ
        backend: RAGBackendインスタンス

    """
    priority_colors = {
        'high': 'border-red-500',
        'medium': 'border-yellow-500',
        'low': 'border-blue-500'
    }
    priority_color = priority_colors.get(todo.get('priority', 'medium'), 'border-slate-500')
    completed_style = 'opacity-50 line-through' if todo.get('completed', False) else ''

    def refresh():
        _render_todo_list(container, stats_container, backend)
        _refresh_todo_stats(stats_container, backend)

    with ui.card().classes(f'w-full p-3 border-l-4 {priority_color} {completed_style}'):
        with ui.row().classes('w-full items-start justify-between'):
            with ui.column().classes('flex-grow gap-1'):
                ui.label(todo.get('title', '無題')).classes('text-sm font-semibold text-white')
                if todo.get('description'):
                    ui.label(todo.get('description', '')).classes('text-xs text-gray-400')
                with ui.row().classes('items-center gap-3 mt-1'):
                    priority_labels = {'high': '高', 'medium': '中', 'low': '低'}
                    priority_label = priority_labels.get(todo.get('priority', 'medium'), '中')
                    ui.label(f'優先度: {priority_label}').classes('text-xs text-gray-400')
                    created = todo.get('created_at', '')
                    ui.label(f'作成: {created[:10] if created else ""}').classes('text-xs text-gray-400')

            with ui.row().classes('items-center gap-1'):
                ui.checkbox(
                    value=todo.get('completed', False),
                    on_change=lambda e, tid=todo['id']: _toggle_completion(backend, tid, refresh)
                ).props('dense color=green-5')
                ui.button(
                    icon='delete',
                    on_click=lambda e, tid=todo['id']: _delete_todo(backend, tid, refresh)
                ).props('flat dense mini color=red-400 size=xs')


def _toggle_completion(backend: RAGBackend, todo_id: str, refresh_func: Callable) -> None:
    """完了状態を切り替える.
 
    Args:
        backend: RAGBackendインスタンス
        todo_id: ToDo ID
        refresh_func: 更新関数
 
    """
    if backend:
        updated = backend.get_todo_service().toggle_todo_completion(todo_id)
        if updated:
            ui.notify('ステータスを更新しました', color='positive')
        refresh_func()


def _delete_todo(backend: RAGBackend, todo_id: str, refresh_func: Callable) -> None:
    """ToDoを削除する.
 
    Args:
        backend: RAGBackendインスタンス
        todo_id: ToDo ID
        refresh_func: 更新関数
 
    """
    if backend:
        success = backend.get_todo_service().delete_todo(todo_id)
        if success:
            ui.notify('削除しました', color='positive')
        refresh_func()


def _refresh_todo_stats(
    container: ui.column,
    backend: RAGBackend,
) -> None:
    """統計情報を更新する.

    Args:
        container: コンテナ
        backend: RAGBackendインスタンス

    """
    container.clear()
    stats = backend.get_todo_service().get_todo_statistics()

    with container:
        with ui.row().classes('w-full gap-4 p-3 bg-gray-700 rounded'):
            ui.label(f'総数: {stats["total"]}').classes('text-xs font-bold text-white')
            ui.label(f'未完了: {stats["pending"]}').classes('text-xs text-amber-400')
            ui.label(f'完了: {stats["completed"]}').classes('text-xs text-green-400')


def _show_add_todo_dialog(
    backend: RAGBackend,
    todo_list_container: ui.column,
    stats_container: ui.column,
) -> None:
    """ToDo追加ダイアログを表示する.

    Args:
        backend: RAGBackendインスタンス
        todo_list_container: ToDo一覧コンテナ
        stats_container: 統計情報コンテナ

    """
    def refresh():
        _render_todo_list(todo_list_container, stats_container, backend)
        _refresh_todo_stats(stats_container, backend)

    with ui.dialog() as dialog, ui.card().classes('w-96 p-4'):
        ui.label('ToDoを追加').classes('text-lg font-bold mb-4')
        title_input = ui.input('タイトル').classes('w-full mb-2')
        desc_input = ui.textarea('説明').classes('w-full mb-2')

        with ui.row().classes('w-full mb-4 items-center'):
            ui.label('優先度:').classes('text-sm')
            priority_toggle = ui.toggle({
                'low': '低',
                'medium': '中',
                'high': '高'
            }, value='medium').props('dense unelevated')

        due_input = ui.input('期限 (YYYY-MM-DD)').classes('w-full mb-4')

        with ui.row().classes('w-full justify-end'):
            ui.button('キャンセル', on_click=dialog.close).props('flat')

            def save():
                if not title_input.value:
                    ui.notify('タイトルを入力してください', color='warning')
                    return
                success = backend.get_todo_service().add_todo(
                    title=title_input.value,
                    description=desc_input.value,
                    priority=priority_toggle.value or 'medium',
                    due_date=due_input.value if due_input.value else None
                )
                if success:
                    ui.notify('追加しました', color='positive')
                    refresh()
                dialog.close()

            ui.button('保存', on_click=save).props('unelevated color=indigo')

    dialog.open()