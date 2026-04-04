"""チャット履歴タブのテスト"""

from collections import Counter
from unittest.mock import Mock, patch, MagicMock
import pytest


class TestChatHistoryTab:
    """チャット履歴タブのテスト."""

    @pytest.fixture
    def mock_backend(self):
        """モックバックエンド."""
        backend = Mock()
        backend.list_chats.return_value = [
            {'id': 'chat-1', 'title': 'Test Chat 1', 'date': '2024-01-01 12:00:00'},
            {'id': 'chat-2', 'title': 'Test Chat 2', 'date': '2024-01-02 12:00:00'},
        ]
        backend.load_chat.return_value = {
            'id': 'chat-1',
            'title': 'Test Chat 1',
            'messages': [
                {'role': 'user', 'content': 'Hello'},
                {'role': 'ai', 'content': 'Hi there!'},
            ],
        }
        backend.delete_chat.return_value = None

        mock_todo_service = Mock()
        mock_todo_service.list_todos.return_value = []
        mock_todo_service.get_todo_statistics.return_value = {
            'total': 0, 'pending': 0, 'completed': 0,
        }
        backend.get_todo_service.return_value = mock_todo_service

        return backend

    @pytest.fixture
    def mock_session(self):
        """モックセッション."""
        return {
            'id': 'current-session',
            'history': [],
        }

    @pytest.fixture
    def mock_state(self):
        """モック状態."""
        return {'hit_counts': Counter()}

    def test_create_chat_history_tab_returns_column(self, mock_backend, mock_session, mock_state):
        """チャット履歴タブがcolumnを返すことをテスト."""
        from src.ui.components.sidebar_tabs.chat_history_tab import create_chat_history_tab

        with patch('src.ui.components.sidebar_tabs.chat_history_tab.ui') as mock_ui:
            mock_container = self._setup_mock_ui(mock_ui)

            result = create_chat_history_tab(mock_backend, mock_session, mock_state)

            assert result is not None

    def test_render_chat_list_shows_chats(self, mock_backend, mock_session):
        """チャット一覧にチャットが表示されることをテスト."""
        from src.ui.components.sidebar_tabs.chat_history_tab import _render_chat_list

        mock_container = MagicMock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=False)
        mock_container.clear = Mock()

        with patch('src.ui.components.sidebar_tabs.chat_history_tab.ui') as mock_ui:
            self._setup_mock_ui_for_list(mock_ui, mock_container)

            _render_chat_list(mock_container, mock_backend, mock_session)

            mock_backend.list_chats.assert_called_once()

    def test_render_chat_list_empty_state(self, mock_backend, mock_session):
        """チャットが存在しない場合の空状態表示をテスト."""
        from src.ui.components.sidebar_tabs.chat_history_tab import _render_chat_list

        mock_backend.list_chats.return_value = []
        mock_container = MagicMock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=False)
        mock_container.clear = Mock()

        with patch('src.ui.components.sidebar_tabs.chat_history_tab.ui') as mock_ui:
            mock_label = Mock()
            mock_ui.label.return_value = mock_label

            _render_chat_list(mock_container, mock_backend, mock_session)

            mock_ui.label.assert_any_call('チャット履歴がありません')

    def test_delete_chat_resets_session(self, mock_backend, mock_session):
        """チャット削除後にセッションがリセットされることをテスト."""
        from src.ui.components.sidebar_tabs.chat_history_tab import _delete_chat

        mock_container = MagicMock()
        mock_session['id'] = 'chat-1'

        _delete_chat('chat-1', mock_backend, mock_session, mock_container)

        mock_backend.delete_chat.assert_called_once_with('chat-1')
        assert mock_session['id'] != 'chat-1'
        assert mock_session['history'] == []

    def test_load_chat_session(self, mock_backend, mock_session):
        """チャットセッションのロードをテスト."""
        from src.ui.components.sidebar_tabs.chat_history_tab import _load_chat

        mock_container = MagicMock()
        mock_chat_results = MagicMock()
        mock_chat_results.clear = Mock()

        # チャット結果コンテナをグローバル参照に設定
        import src.ui.components.sidebar_tabs.chat_history_tab as chat_module
        chat_module._chat_results_ref['container'] = mock_chat_results

        _load_chat('chat-1', mock_backend, mock_session, mock_container)

        assert mock_session['id'] == 'chat-1'
        assert len(mock_session['history']) == 2

    def test_start_new_chat(self, mock_backend, mock_session):
        """新しいチャットの開始をテスト."""
        from src.ui.components.sidebar_tabs.chat_history_tab import _start_new_chat

        mock_container = MagicMock()
        old_session_id = mock_session['id']

        _start_new_chat(mock_session, mock_container)

        assert mock_session['id'] != old_session_id
        assert mock_session['history'] == []

    def _setup_mock_ui(self, mock_ui):
        """UIモックを設定する."""
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = Mock(return_value=mock_context_manager)
        mock_context_manager.__exit__ = Mock(return_value=False)

        mock_ui.left_drawer.return_value = mock_context_manager
        mock_ui.tabs.return_value = mock_context_manager
        mock_ui.tab.return_value = mock_context_manager
        mock_ui.tab_panels.return_value = mock_context_manager
        mock_ui.column.return_value = mock_context_manager
        mock_ui.label.return_value = mock_context_manager
        mock_ui.button.return_value = mock_context_manager
        mock_ui.icon.return_value = mock_context_manager
        mock_ui.row.return_value = mock_context_manager
        mock_ui.dialog.return_value.__enter__ = Mock(return_value=mock_context_manager)
        mock_ui.dialog.return_value.__exit__ = Mock(return_value=False)

        return mock_context_manager

    def _setup_mock_ui_for_list(self, mock_ui, mock_container):
        """チャットリスト表示用のUIモック."""
        mock_ui.label.return_value = Mock()
        mock_ui.row.return_value = mock_container
        mock_ui.icon.return_value = Mock()
        mock_ui.button.return_value = Mock()