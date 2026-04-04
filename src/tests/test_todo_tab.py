"""ToDoタブのテスト"""

from unittest.mock import Mock, patch, MagicMock
import pytest


class TestTodoTab:
    """ToDoタブのテスト."""

    @pytest.fixture
    def mock_backend(self):
        """モックバックエンド."""
        backend = Mock()

        mock_todo_service = Mock()
        mock_todo_service.add_todo.return_value = True
        mock_todo_service.delete_todo.return_value = True
        mock_todo_service.toggle_todo_completion.return_value = True
        mock_todo_service.list_todos.return_value = [
            {'id': 'todo-1', 'title': 'Test Todo 1', 'priority': 'high', 'completed': False},
            {'id': 'todo-2', 'title': 'Test Todo 2', 'priority': 'medium', 'completed': False},
        ]
        mock_todo_service.get_todo_statistics.return_value = {
            'total': 2, 'pending': 2, 'completed': 0,
            'priority_distribution': {'high': 1, 'medium': 1, 'low': 0},
        }
        backend.get_todo_service.return_value = mock_todo_service

        return backend

    def test_create_todo_tab_returns_column(self, mock_backend):
        """ToDoタブがcolumnを返すことをテスト."""
        from src.ui.components.sidebar_tabs.todo_tab import create_todo_tab

        with patch('src.ui.components.sidebar_tabs.todo_tab.ui') as mock_ui:
            mock_container = self._setup_mock_ui(mock_ui)

            result = create_todo_tab(mock_backend)

            assert result is not None

    def test_render_todo_list_shows_todos(self, mock_backend):
        """ToDo一覧が表示されることをテスト."""
        from src.ui.components.sidebar_tabs.todo_tab import _render_todo_list

        mock_list_container = MagicMock()
        mock_list_container.__enter__ = Mock(return_value=mock_list_container)
        mock_list_container.__exit__ = Mock(return_value=False)
        mock_list_container.clear = Mock()

        mock_stats_container = MagicMock()
        mock_stats_container.__enter__ = Mock(return_value=mock_stats_container)
        mock_stats_container.__exit__ = Mock(return_value=False)
        mock_stats_container.clear = Mock()

        with patch('src.ui.components.sidebar_tabs.todo_tab.ui') as mock_ui:
            self._setup_mock_ui_for_list(mock_ui, mock_list_container)

            _render_todo_list(mock_list_container, mock_stats_container, mock_backend)

            mock_backend.get_todo_service().list_todos.assert_called_once()

    def test_render_todo_list_empty_state(self, mock_backend):
        """ToDoが存在しない場合の空状態表示をテスト."""
        from src.ui.components.sidebar_tabs.todo_tab import _render_todo_list

        mock_backend.get_todo_service().list_todos.return_value = []

        mock_list_container = MagicMock()
        mock_list_container.__enter__ = Mock(return_value=mock_list_container)
        mock_list_container.__exit__ = Mock(return_value=False)
        mock_list_container.clear = Mock()

        mock_stats_container = MagicMock()
        mock_stats_container.__enter__ = Mock(return_value=mock_stats_container)
        mock_stats_container.__exit__ = Mock(return_value=False)
        mock_stats_container.clear = Mock()

        with patch('src.ui.components.sidebar_tabs.todo_tab.ui') as mock_ui:
            mock_ui.label.return_value = Mock()

            _render_todo_list(mock_list_container, mock_stats_container, mock_backend)

            mock_ui.label.assert_any_call('ToDoがありません')

    def test_toggle_todo(self, mock_backend):
        """ToDoの完了状態切り替えをテスト."""
        from src.ui.components.sidebar_tabs.todo_tab import _toggle_todo

        mock_list_container = MagicMock()
        mock_stats_container = MagicMock()

        _toggle_todo('todo-1', True, mock_backend, mock_list_container, mock_stats_container)

        mock_backend.get_todo_service().toggle_todo_completion.assert_called_once_with('todo-1')

    def test_delete_todo(self, mock_backend):
        """ToDoの削除をテスト."""
        from src.ui.components.sidebar_tabs.todo_tab import _delete_todo

        mock_list_container = MagicMock()
        mock_stats_container = MagicMock()

        _delete_todo('todo-1', mock_backend, mock_list_container, mock_stats_container)

        mock_backend.get_todo_service().delete_todo.assert_called_once_with('todo-1')

    def test_add_todo(self, mock_backend):
        """ToDoの追加をテスト."""
        from src.ui.components.sidebar_tabs.todo_tab import _add_todo

        mock_list_container = MagicMock()
        mock_stats_container = MagicMock()
        mock_dialog = Mock()

        _add_todo('New Todo', 'high', mock_backend, mock_dialog, mock_list_container, mock_stats_container)

        mock_backend.get_todo_service().add_todo.assert_called_once_with(title='New Todo', priority='high')
        mock_dialog.close.assert_called_once()

    def test_add_todo_empty_title(self, mock_backend):
        """空タイトルのToDo追加をテスト."""
        from src.ui.components.sidebar_tabs.todo_tab import _add_todo

        mock_list_container = MagicMock()
        mock_stats_container = MagicMock()
        mock_dialog = Mock()

        with patch('src.ui.components.sidebar_tabs.todo_tab.ui') as mock_ui:
            mock_notify = Mock()
            mock_ui.notify = mock_notify

            _add_todo('', 'high', mock_backend, mock_dialog, mock_list_container, mock_stats_container)

            mock_notify.assert_called_once()
            mock_backend.get_todo_service().add_todo.assert_not_called()

    def _setup_mock_ui(self, mock_ui):
        """UIモックを設定する."""
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = Mock(return_value=mock_context_manager)
        mock_context_manager.__exit__ = Mock(return_value=False)

        mock_ui.column.return_value = mock_context_manager
        mock_ui.label.return_value = mock_context_manager
        mock_ui.button.return_value = mock_context_manager
        mock_ui.row.return_value = mock_context_manager
        mock_ui.checkbox.return_value = mock_context_manager
        mock_ui.icon.return_value = mock_context_manager
        mock_ui.dialog.return_value.__enter__ = Mock(return_value=mock_context_manager)
        mock_ui.dialog.return_value.__exit__ = Mock(return_value=False)
        mock_ui.card.return_value = mock_context_manager
        mock_ui.input.return_value = mock_context_manager
        mock_ui.select.return_value = mock_context_manager

        return mock_context_manager

    def _setup_mock_ui_for_list(self, mock_ui, mock_container):
        """ToDoリスト表示用のUIモック."""
        mock_ui.label.return_value = Mock()
        mock_ui.row.return_value = mock_container
        mock_ui.checkbox.return_value = Mock()
        mock_ui.icon.return_value = Mock()
        mock_ui.button.return_value = Mock()