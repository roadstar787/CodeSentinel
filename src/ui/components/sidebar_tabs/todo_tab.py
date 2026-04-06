"""ToDoタブUIコンポーネント"""

from typing import Any, Dict, Optional, Tuple

from nicegui import ui


def create_todo_tab(
    backend: Any,
) -> Tuple[ui.column, ui.row]:
    """ToDoタブを作成する.

    Args:
        backend: RAGBackendインスタンス

    Returns:
        (todo_list_container, todo_stats_container)

    """
    # ソートオプションとフィルターを保持する変数
    sort_select: Any = None
    show_completed_toggle: Any = None

    def _show_edit_dialog(todo: Dict[str, Any]) -> None:
        """ToDo編集ダイアログを表示."""
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label('Edit ToDo').classes('text-lg font-bold mb-4')
            title_input = ui.input('タイトル', value=todo.get('title', '')).classes('w-full mb-2')
            desc_input = ui.textarea('説明', value=todo.get('description', '')).classes('w-full mb-2')

            priority_toggle = ui.toggle(
                {'low': '低', 'medium': '中', 'high': '高'},
                value=todo.get('priority', 'medium')
            ).props('dense unelevated').classes('mb-4')

            due_date_input = ui.input('期限 (YYYY-MM-DD)', value=todo.get('due_date', '')).classes('w-full mb-4')

            with ui.row().classes('w-full justify-end'):
                ui.button('キャンセル', on_click=dialog.close).props('flat')

                def _save():
                    todo_service = backend.get_todo_service() if backend else None
                    if todo_service:
                        todo_service.update_todo(
                            todo['id'],
                            title=title_input.value,
                            description=desc_input.value,
                            priority=priority_toggle.value,
                            due_date=due_date_input.value if due_date_input.value else None,
                        )
                        # ステートを更新
                        backend.stats['todos'] = todo_service.list_todos()
                    ui.notify('ToDoを更新しました')
                    dialog.close()

                ui.button('更新', on_click=_save).props('unelevated color=indigo')
        dialog.open()

    # UI要素を作成
    def _build_ui():
        with ui.column().classes('w-full gap-2'):
            # ヘッダー行（タイトルと追加ボタン）
            with ui.row().classes('w-full items-center justify-between mb-2'):
                with ui.row().classes('gap-2'):
                    sort_options = {
                        'created_at_desc': '作成日時 (新しい順)',
                        'created_at_asc': '作成日時 (古い順)',
                        'updated_at_desc': '更新日時 (新しい順)',
                        'updated_at_asc': '更新日時 (古い順)',
                        'priority_desc': '優先度 (高→低)',
                        'priority_asc': '優先度 (低→高)',
                        'due_date_asc': '期限 (近い順)',
                    }
                    nonlocal sort_select, show_completed_toggle
                    sort_select = ui.select(
                        options=sort_options,
                        value='created_at_desc',
                        label='ソート',
                    ).props('dense outlined mini').classes('text-xs')
                    sort_select.on('change', lambda e: _refresh_todo_list())

                show_completed_toggle = ui.toggle(
                    options={True: '完了済みを表示', False: '未完了のみ'},
                    value=True,
                ).props('dense mini').classes('text-xs')
                show_completed_toggle.on('change', lambda e: _refresh_todo_list())

            # ToDo追加ボタン
            ui.button(
                icon='add',
                on_click=lambda: _show_add_todo_dialog()
            ).props('flat round dense color=slate-400 mb-2')

            # 統計情報コンテナ
            # 中身は_refresh_todo_listで描画

            # ToDoリストコンテナ
            # 中身は_refresh_todo_listで描画

    _build_ui()

    def _refresh_todo_list() -> None:
        """ToDoリストと統計情報を更新."""
        todo_service = backend.get_todo_service() if backend else None
        if todo_service is None:
            return

        # ソートオプションを取得
        sort_value = sort_select.value if sort_select else 'created_at_desc'
        show_completed = show_completed_toggle.value if show_completed_toggle else True

        # ソートオプションを解析
        try:
            sort_by, sort_order = sort_value.rsplit('_', 1)
        except Exception:
            sort_by = 'created_at'
            sort_order = 'desc'

        # ToDoリストを取得
        todos = todo_service.list_todos(
            show_completed=show_completed,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # 統計情報を更新
        _render_todo_stats()

        # リストを更新
        todo_list_container.clear()
        with todo_list_container:
            if not todos:
                ui.label('ToDoがありません').classes('text-gray-400 text-sm p-2')
            else:
                for todo in todos[:20]:
                    _render_todo_item(todo)

    def _render_todo_stats() -> None:
        """統計情報を描画."""
        todo_service = backend.get_todo_service() if backend else None
        if todo_service is None:
            return

        stats = todo_service.get_todo_statistics()

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
                    pd = stats.get('priority_distribution', {})
                    high_color = 'text-red-400' if pd.get('high', 0) > 0 else 'text-slate-600'
                    ui.label(f'高: {pd.get("high", 0)}').classes(f'text-xs {high_color}')
                    medium_color = 'text-yellow-400' if pd.get('medium', 0) > 0 else 'text-slate-600'
                    ui.label(f'中: {pd.get("medium", 0)}').classes(f'text-xs {medium_color}')
                    low_color = 'text-blue-400' if pd.get('low', 0) > 0 else 'text-slate-600'
                    ui.label(f'低: {pd.get("low", 0)}').classes(f'text-xs {low_color}')

    def _render_todo_item(todo: Dict[str, Any]) -> None:
        """ToDoアイテムを描画."""
        from datetime import datetime

        priority_colors = {
            'high': 'border-red-500',
            'medium': 'border-yellow-500',
            'low': 'border-blue-500',
        }
        priority_color = priority_colors.get(todo.get('priority', 'medium'), 'border-slate-500')
        completed = todo.get('completed', False)
        completed_style = 'opacity-60' if completed else ''

        with ui.card().classes(f'w-full p-3 border-l-4 {priority_color} {completed_style}'):
            # タイトル行（編集ボタン付き）
            with ui.row().classes('w-full items-start justify-between'):
                # 左側：TODO内容
                with ui.column().classes('flex-grow gap-1'):
                    # タイトル
                    title = todo.get('title', '無題')
                    title_label = ui.label(title).classes('text-sm font-semibold text-white')
                    if completed:
                        title_label.classes('text-gray-400 line-through')

                    # 説明
                    desc = todo.get('description', '')
                    if desc:
                        ui.label(desc).classes('text-xs text-slate-400 leading-relaxed')

                    # メタ情報（優先度、作成日時、期限）
                    with ui.row().classes('items-center gap-3 mt-1'):
                        priority_labels = {'high': '高', 'medium': '中', 'low': '低'}
                        priority_label_text = priority_labels.get(todo.get('priority', 'medium'), '中')
                        priority_classes = {
                            'high': 'text-red-400',
                            'medium': 'text-yellow-400',
                            'low': 'text-blue-400'
                        }
                        p_class = priority_classes.get(todo.get('priority', 'medium'), 'text-slate-400')
                        ui.label(f'優先度: {priority_label_text}').classes(f'text-xs {p_class}')

                        created = todo.get('created_at', '')
                        if created:
                            ui.label(created[:10]).classes('text-xs text-slate-500')

                        due_date = todo.get('due_date')
                        if due_date:
                            today = datetime.now().strftime('%Y-%m-%d')
                            try:
                                if due_date < today and not completed:
                                    due_color = 'text-red-400'
                                else:
                                    due_color = 'text-slate-400'
                                ui.label(f'期限: {due_date}').classes(f'text-xs {due_color}')
                            except Exception:
                                ui.label(f'期限: {due_date}').classes('text-xs text-slate-400')

                # 右側：操作ボタン
                with ui.row().classes('items-center gap-1'):
                    todo_id = todo.get('id', '')

                    # 完了チェックボックス
                    ui.checkbox(
                        value=completed,
                        on_change=lambda e, tid=todo_id: _toggle_todo(tid, e.value)
                    ).props('dense color=green').classes('text-green-400')

                    # 編集ボタン
                    ui.button(
                        icon='edit',
                        on_click=lambda e, t=todo: _show_edit_dialog(t)
                    ).props('flat dense mini color=slate-400 size=xs')

                    # 削除ボタン
                    ui.button(
                        icon='delete',
                        on_click=lambda e, tid=todo_id: _delete_todo(tid)
                    ).props('flat dense mini color=red-4 size=xs')

    def _toggle_todo(todo_id: str, completed: bool) -> None:
        """ToDoの完了状態を切り替え."""
        todo_service = backend.get_todo_service() if backend else None
        if todo_service:
            todo_service.toggle_todo_completion(todo_id)
            # ステートを更新
            backend.stats['todos'] = todo_service.list_todos()

    def _delete_todo(todo_id: str) -> None:
        """ToDoを削除."""
        todo_service = backend.get_todo_service() if backend else None
        if todo_service:
            todo_service.delete_todo(todo_id)
            # ステートを更新
            backend.stats['todos'] = todo_service.list_todos()
        ui.notify('ToDoを削除しました')

    def _show_add_todo_dialog() -> None:
        """ToDo追加ダイアログを表示."""
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label('新しいToDo').classes('text-lg font-bold mb-4')
            title_input = ui.input('タイトル').classes('w-full mb-2')
            desc_input = ui.textarea('説明（任意）').classes('w-full mb-2')
            priority_toggle = ui.toggle(
                {'low': '低', 'medium': '中', 'high': '高'},
                value='medium'
            ).props('dense unelevated').classes('mb-4')
            due_date_input = ui.input('期限（YYYY-MM-DD形式）').classes('w-full mb-4')

            with ui.row().classes('w-full justify-end'):
                ui.button('キャンセル', on_click=dialog.close).props('flat')

                def _save():
                    if not title_input.value:
                        ui.notify('タイトルを入力してください', color='warning')
                        return
                    todo_service = backend.get_todo_service() if backend else None
                    if todo_service:
                        todo_service.add_todo(
                            title=title_input.value,
                            description=desc_input.value,
                            priority=priority_toggle.value,
                            due_date=due_date_input.value if due_date_input.value else None,
                        )
                        # ステートを更新
                        backend.stats['todos'] = todo_service.list_todos()
                    ui.notify('ToDoを追加しました')
                    dialog.close()

                ui.button('追加', on_click=_save).props('unelevated color=indigo')
        dialog.open()

    # ToDoリストの表示コンテナ作成
    todo_stats_container = ui.row().classes('w-full gap-4 mb-4')
    todo_list_container = ui.column().classes('w-full gap-2')

    @ui.refreshable
    def render_todo_list():
        _refresh_todo_list()

    # ToDoリストの変更を監視する
    last_todo_count = [len(backend.stats.get('todos', [])) if backend and hasattr(backend, 'stats') else 0]
    last_todo_ids = [str([t.get('id') for t in backend.stats.get('todos', [])]) if backend and hasattr(backend, 'stats') else "[]"]

    def check_todo_state():
        if not backend: return
        current_todos = backend.stats.get('todos', [])
        current_count = len(current_todos)
        current_ids = str([t.get('id') for t in current_todos])
        
        if current_count != last_todo_count[0] or current_ids != last_todo_ids[0]:
            last_todo_count[0] = current_count
            last_todo_ids[0] = current_ids
            render_todo_list.refresh()

    ui.timer(1.0, check_todo_state)

    # 初期表示
    render_todo_list()

    return todo_list_container, todo_stats_container