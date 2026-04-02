"""UIコンポーネントのテスト"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.config.settings import Settings
from src.core.backend import RAGBackend
from src.ui.components.sidebar import create_sidebar


class TestSidebar:
    """サイドバーコンポーネントのテスト."""

    @pytest.fixture
    def mock_backend(self):
        """モックバックエンド."""
        backend = Mock(spec=RAGBackend)
        backend.list_chats.return_value = [
            {'id': '1', 'title': 'Test Chat 1', 'date': '2024-01-01 12:00:00'},
            {'id': '2', 'title': 'Test Chat 2', 'date': '2024-01-02 12:00:00'}
        ]
        backend.get_user_settings.return_value = {
            'target_dir': '/test/path',
            'doc_dir': '/doc/path',
            'mode': 'Normal'
        }
        mock_doc_service = Mock()
        mock_doc_service.get_statistics.return_value = {
            'total_chunks': 100,
            'vector_store_loaded': True,
            'lm_connected': True
        }
        backend.get_document_service.return_value = mock_doc_service

        mock_todo_service = Mock()
        mock_todo_service.list_todos.return_value = [
            {'id': '1', 'title': 'Test Todo', 'completed': False, 'priority': 'high'}
        ]
        mock_todo_service.get_todo_statistics.return_value = {
            'total': 1,
            'pending': 1,
            'completed': 0,
            'priority_distribution': {'high': 1, 'medium': 0, 'low': 0}
        }
        backend.get_todo_service.return_value = mock_todo_service
        return backend

    def test_create_sidebar_returns_correct_structure(self, mock_backend):
        """サイドバーが正しい構造を返すことをテスト."""
        # NiceGUIのUI要素をモック
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = Mock(return_value=mock_context_manager)
        mock_context_manager.__exit__ = Mock(return_value=False)

        mock_tab = Mock()
        mock_tab_panel = MagicMock()
        mock_tab_panel.__enter__ = Mock(return_value=mock_tab_panel)
        mock_tab_panel.__exit__ = Mock(return_value=False)

        mock_tabs = MagicMock()
        mock_tabs.__enter__ = Mock(return_value=mock_tabs)
        mock_tabs.__exit__ = Mock(return_value=False)

        with patch('src.ui.components.sidebar.ui') as mock_ui:
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
            mock_ui.space.return_value = mock_context_manager

            # テスト実行
            result = create_sidebar(mock_backend)

            # 検証
            assert len(result) == 8
            assert mock_ui.left_drawer.called
            assert mock_ui.tabs.called
            assert mock_ui.tab_panels.called
            assert mock_ui.tab.call_count >= 5  # 5つのタブ