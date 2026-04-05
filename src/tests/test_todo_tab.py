"""ToDoタブのテスト"""

from unittest.mock import Mock, patch, MagicMock, call
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

    def test_create_todo_tab_returns_containers(self, mock_backend):
        """ToDoタブがコンテナのタプルを返すことをテスト."""
        from src.ui.components.sidebar_tabs.todo_tab import create_todo_tab

        with patch('src.ui.components.sidebar_tabs.todo_tab.ui') as mock_ui:
            self._setup_mock_ui(mock_ui)

            result = create_todo_tab(mock_backend)

            # 2つのコンテナが返されることを確認
            assert result is not None
            assert len(result) == 2
            # 各要素がui.columnまたはui.rowのモックであることを確認
            assert result[0] is not None
            assert result[1] is not None

    def test_create_todo_tab_initializes_ui(self, mock_backend):
        """UIが正しく初期化されることをテスト."""
        from src.ui.components.sidebar_tabs.todo_tab import create_todo_tab

        with patch('src.ui.components.sidebar_tabs.todo_tab.ui') as mock_ui:
            self._setup_mock_ui(mock_ui)

            # バックエンドのサービスが呼ばれることを確認
            create_todo_tab(mock_backend)

            # サービスが呼ばれることを確認
            mock_backend.get_todo_service.assert_called()

    def test_create_todo_tab_handles_no_backend(self):
        """バックエンドがNoneの場合のテスト."""
        from src.ui.components.sidebar_tabs.todo_tab import create_todo_tab

        with patch('src.ui.components.sidebar_tabs.todo_tab.ui') as mock_ui:
            self._setup_mock_ui(mock_ui)

            # Noneが渡されてもエラーにならないことを確認
            try:
                result = create_todo_tab(None)
                assert result is not None
            except Exception:
                # エラーが発生する場合は、適切な処理が必要
                pytest.fail("create_todo_tab raised an exception with None backend")

    def _setup_mock_ui(self, mock_ui):
        """UIモックを設定する."""
        # コンテナを作成するモック
        mock_list_container = MagicMock()
        mock_list_container.clear = Mock()
        mock_stats_container = MagicMock()
        mock_stats_container.clear = Mock()

        # column/rowはコンテキストマネージャとして動作
        def make_container(name):
            cm = MagicMock()
            cm.__enter__ = Mock(return_value=cm)
            cm.__exit__ = Mock(return_value=False)
            cm.clear = Mock()
            cm.classes = Mock(return_value=cm)
            return cm

        mock_column = make_container('column')
        mock_row = make_container('row')

        # ui.column()とui.row()はコンテキストマネージャを返す
        mock_ui.column.return_value = mock_column
        mock_ui.row.return_value = mock_row

        # 各種UI要素のモック
        mock_label = MagicMock()
        mock_label.classes = Mock(return_value=mock_label)
        mock_ui.label.return_value = mock_label

        mock_button = MagicMock()
        mock_button.props = Mock(return_value=mock_button)
        mock_button.classes = Mock(return_value=mock_button)
        mock_ui.button.return_value = mock_button

        mock_select = MagicMock()
        mock_select.props = Mock(return_value=mock_select)
        mock_select.classes = Mock(return_value=mock_select)
        mock_select.on = Mock(return_value=mock_select)
        mock_select.value = 'created_at_desc'
        mock_ui.select.return_value = mock_select

        mock_toggle = MagicMock()
        mock_toggle.props = Mock(return_value=mock_toggle)
        mock_toggle.classes = Mock(return_value=mock_toggle)
        mock_toggle.on = Mock(return_value=mock_toggle)
        mock_toggle.value = True
        mock_ui.toggle.return_value = mock_toggle

        mock_checkbox = MagicMock()
        mock_checkbox.classes = Mock(return_value=mock_checkbox)
        mock_ui.checkbox.return_value = mock_checkbox

        mock_icon = MagicMock()
        mock_ui.icon.return_value = mock_icon

        mock_dialog_cm = MagicMock()
        mock_dialog_cm.__enter__ = Mock(return_value=mock_dialog_cm)
        mock_dialog_cm.__exit__ = Mock(return_value=False)
        mock_dialog_cm.open = Mock()
        mock_dialog_cm.close = Mock()
        mock_ui.dialog.return_value.__enter__ = Mock(return_value=mock_dialog_cm)
        mock_ui.dialog.return_value.__exit__ = Mock(return_value=False)

        mock_card = make_container('card')
        mock_ui.card.return_value = mock_card

        mock_input = MagicMock()
        mock_input.props = Mock(return_value=mock_input)
        mock_input.value = 'test value'
        mock_ui.input.return_value = mock_input

        mock_notify = Mock()
        mock_ui.notify = mock_notify

        return mock_ui