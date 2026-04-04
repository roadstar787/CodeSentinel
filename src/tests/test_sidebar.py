"""サイドバーコンポーネントのテスト"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestSidebarChatIntegration:
    """サイドバーとチャット履歴の連係テスト."""

    @pytest.fixture
    def mock_backend(self):
        """モックバックエンド."""
        backend = Mock()
        backend.list_chats.return_value = [
            {'id': 'chat-1', 'title': 'Test Chat 1', 'date': '2024-01-01 12:00:00'},
            {'id': 'chat-2', 'title': 'Test Chat 2', 'date': '2024-01-02 12:00:00'}
        ]
        backend.load_chat.return_value = {
            'id': 'chat-1',
            'title': 'Test Chat 1',
            'messages': [
                {'role': 'user', 'content': 'Hello'},
                {'role': 'ai', 'content': 'Hi there!'}
            ]
        }
        backend.get_user_settings.return_value = {
            'target_dir': '/test/path',
            'doc_dir': '/doc/path',
            'mode': 'Normal'
        }
        backend.delete_chat.return_value = None

        mock_todo_service = Mock()
        mock_todo_service.list_todos.return_value = []
        mock_todo_service.get_todo_statistics.return_value = {
            'total': 0, 'pending': 0, 'completed': 0,
            'priority_distribution': {'high': 0, 'medium': 0, 'low': 0}
        }
        backend.get_todo_service.return_value = mock_todo_service

        mock_doc_service = Mock()
        mock_doc_service.get_statistics.return_value = {
            'total_chunks': 0, 'vector_store_loaded': False, 'lm_connected': False
        }
        backend.get_document_service.return_value = mock_doc_service

        return backend

    @pytest.fixture
    def mock_session(self):
        """モックセッション."""
        return {
            'id': 'current-session',
            'history': []
        }

    @pytest.fixture
    def mock_state(self):
        """モック状態."""
        return {'hit_counts': {}}

    def test_create_sidebar_accepts_session_and_state(self, mock_backend, mock_session, mock_state):
        """create_sidebarがsessionとstateパラメータを受け取ることをテスト."""
        from src.ui.components.sidebar import create_sidebar

        with patch('src.ui.components.sidebar.ui') as mock_ui:
            self._setup_mock_ui(mock_ui)

            # sessionとstateを渡して呼び出し
            result = create_sidebar(mock_backend, session=mock_session, state=mock_state)

            # 戻り値の検証
            assert result is not None

    def test_chat_list_renders_with_session(self, mock_backend, mock_session, mock_state):
        """チャット一覧がsessionコンテキストで正しくレンダリングされることをテスト."""
        from src.ui.components.sidebar import create_sidebar
        from src.ui.components.sidebar_tabs.chat_history_tab import _render_chat_list

        with patch('src.ui.components.sidebar.ui') as mock_ui:
            self._setup_mock_ui(mock_ui)

            # チャットリストコンテナをキャプチャ
            mock_container = MagicMock()
            mock_container.__enter__ = Mock(return_value=mock_container)
            mock_container.__exit__ = Mock(return_value=False)
            mock_container.clear = Mock()
            mock_ui.column.return_value = mock_container

            create_sidebar(mock_backend, session=mock_session, state=mock_state)

            # _render_chat_listを直接呼び出してテスト
            _render_chat_list(mock_container, mock_backend, mock_session)

            # チャットリストがレンダリングされていることを確認
            assert mock_backend.list_chats.called

    def test_chat_delete_updates_session(self, mock_backend, mock_session, mock_state):
        """チャット削除後にセッションがリセットされることをテスト."""
        from src.ui.components.sidebar_tabs.chat_history_tab import _delete_chat

        mock_chat_results = MagicMock()
        mock_chat_list_container = MagicMock()

        # 現在のセッションIDと一致するチャットを削除
        mock_session['id'] = 'chat-1'

        _delete_chat(
            chat_id='chat-1',
            backend=mock_backend,
            session=mock_session,
            container=mock_chat_list_container,
        )

        # チャット削除が呼ばれていることを確認
        mock_backend.delete_chat.assert_called_with('chat-1')
        # セッションが新しいIDにリセットされていることを確認
        assert mock_session['id'] != 'chat-1'
        assert 'history' in mock_session

    def test_render_chat_list_shows_chats(self, mock_backend, mock_session, mock_state):
        """チャット一覧にチャットが表示されることをテスト."""
        from src.ui.components.sidebar_tabs.chat_history_tab import _render_chat_list

        mock_container = MagicMock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=False)
        mock_container.clear = Mock()

        with patch('src.ui.components.sidebar_tabs.chat_history_tab.ui') as mock_ui:
            mock_ui.label.return_value = MagicMock()
            mock_ui.row.return_value = mock_container
            mock_ui.icon.return_value = MagicMock()
            mock_ui.button.return_value = MagicMock()

            _render_chat_list(
                container=mock_container,
                backend=mock_backend,
                session=mock_session,
            )

            # チャット一覧が取得されていることを確認
            assert mock_backend.list_chats.called

    def test_render_chat_list_empty_state(self, mock_backend, mock_session, mock_state):
        """チャットが存在しない場合の空状態表示をテスト."""
        from src.ui.components.sidebar_tabs.chat_history_tab import _render_chat_list

        mock_backend.list_chats.return_value = []
        mock_container = MagicMock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=False)
        mock_container.clear = Mock()

        with patch('src.ui.components.sidebar_tabs.chat_history_tab.ui') as mock_ui:
            mock_ui.label.return_value = MagicMock()

            _render_chat_list(
                container=mock_container,
                backend=mock_backend,
                session=mock_session,
            )

            # 空状態メッセージが表示されていることを確認
            mock_ui.label.assert_any_call('チャット履歴がありません')

    def _setup_mock_ui(self, mock_ui):
        """UIモックを設定する."""
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = Mock(return_value=mock_context_manager)
        mock_context_manager.__exit__ = Mock(return_value=False)

        mock_tab = MagicMock()

        mock_tabs = MagicMock()
        mock_tabs.__enter__ = Mock(return_value=mock_tabs)
        mock_tabs.__exit__ = Mock(return_value=False)

        mock_tab_panel = MagicMock()
        mock_tab_panel.__enter__ = Mock(return_value=mock_tab_panel)
        mock_tab_panel.__exit__ = Mock(return_value=False)

        mock_ui.left_drawer.return_value = mock_context_manager
        mock_ui.tabs.return_value = mock_tabs
        mock_ui.tab.return_value = mock_tab
        mock_ui.tab_panels.return_value = mock_tab_panel
        mock_ui.column.return_value = mock_context_manager
        mock_ui.label.return_value = mock_context_manager
        mock_ui.button.return_value = mock_context_manager
        mock_ui.icon.return_value = mock_context_manager
        mock_ui.row.return_value = mock_context_manager
        mock_ui.checkbox.return_value = mock_context_manager
        mock_ui.select.return_value = mock_context_manager
        mock_ui.input.return_value = mock_context_manager
        mock_ui.space.return_value = mock_context_manager
        mock_ui.card.return_value = mock_context_manager
        mock_ui.textarea.return_value = mock_context_manager
        mock_ui.toggle.return_value = mock_context_manager
        mock_ui.dialog.return_value.__enter__ = Mock(return_value=mock_context_manager)
        mock_ui.dialog.return_value.__exit__ = Mock(return_value=False)
        mock_ui.tree.return_value = mock_context_manager