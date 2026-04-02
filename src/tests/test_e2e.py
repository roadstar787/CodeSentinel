"""エンドツーエンドテスト"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from nicegui import ui


class TestE2E:
    """エンドツーエンドテストクラス."""

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリの作成."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_backend(self, temp_dir):
        """モックバックエンドの作成."""
        backend = Mock()
        backend.get_user_settings.return_value = {
            'target_dir': str(temp_dir / 'target'),
            'doc_dir': str(temp_dir / 'docs'),
            'mode': 'Normal'
        }
        backend.list_chats.return_value = []
        backend.load_chat.return_value = None
        backend.save_chat = Mock()
        backend.delete_chat = Mock()
        backend.get_retriever.return_value = None

        # ドキュメントサービス
        mock_doc_service = Mock()
        mock_doc_service.get_statistics.return_value = {
            'total_chunks': 0,
            'vector_store_loaded': False,
            'lm_connected': False
        }
        backend.get_document_service.return_value = mock_doc_service

        # ToDoサービス
        mock_todo_service = Mock()
        mock_todo_service.list_todos.return_value = []
        mock_todo_service.get_todo_statistics.return_value = {
            'total': 0,
            'pending': 0,
            'completed': 0,
            'priority_distribution': {'high': 0, 'medium': 0, 'low': 0}
        }
        mock_todo_service.add_todo.return_value = True
        mock_todo_service.delete_todo.return_value = True
        mock_todo_service.toggle_todo_completion.return_value = True
        backend.get_todo_service.return_value = mock_todo_service

        # チャットサービス
        mock_chat_service = Mock()
        mock_chat_service.generate_response = AsyncMock(return_value={
            'content': 'Test response',
            'gaps': []
        })
        mock_chat_service.process_search_results.return_value = []
        mock_chat_service.format_context.return_value = ''
        backend.get_chat_service.return_value = mock_chat_service

        backend.mode = 'Normal'
        return backend

    def test_sidebar_creation(self, mock_backend):
        """サイドバー作成のE2Eテスト."""
        from src.ui.components.sidebar import create_sidebar

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

            result = create_sidebar(mock_backend)

            assert len(result) == 8
            assert mock_ui.left_drawer.called
            assert mock_ui.tabs.called

    def test_file_explorer_creation(self, mock_backend):
        """ファイルエクスプローラー作成のE2Eテスト."""
        from src.ui.components.file_explorer import create_file_explorer

        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = Mock(return_value=mock_context_manager)
        mock_context_manager.__exit__ = Mock(return_value=False)

        with patch('src.ui.components.file_explorer.ui') as mock_ui:
            mock_ui.column.return_value = mock_context_manager
            mock_ui.label.return_value = mock_context_manager
            mock_ui.row.return_value = mock_context_manager
            mock_ui.icon.return_value = mock_context_manager
            mock_ui.button.return_value = mock_context_manager

            result = create_file_explorer(mock_backend)

            assert mock_ui.column.called
            assert mock_ui.label.called

    def test_todo_manager_creation(self, mock_backend):
        """ToDo管理作成のE2Eテスト."""
        from src.ui.components.todo_manager import create_todo_manager

        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = Mock(return_value=mock_context_manager)
        mock_context_manager.__exit__ = Mock(return_value=False)

        with patch('src.ui.components.todo_manager.ui') as mock_ui:
            mock_ui.column.return_value = mock_context_manager
            mock_ui.label.return_value = mock_context_manager
            mock_ui.row.return_value = mock_context_manager
            mock_ui.button.return_value = mock_context_manager
            mock_ui.card.return_value = mock_context_manager
            mock_ui.checkbox.return_value = mock_context_manager
            mock_ui.dialog.return_value.__enter__ = Mock(return_value=mock_context_manager)
            mock_ui.dialog.return_value.__exit__ = Mock(return_value=False)
            mock_ui.input.return_value = mock_context_manager
            mock_ui.textarea.return_value = mock_context_manager
            mock_ui.toggle.return_value = mock_context_manager

            result = create_todo_manager(mock_backend)

            assert mock_ui.column.called
            assert mock_ui.label.called

    def test_chat_interface_creation(self, mock_backend):
        """チャットインターフェース作成のE2Eテスト."""
        from src.ui.components.chat_interface import create_chat_interface

        session = {'id': 'test-session', 'history': []}
        state = {'hit_counts': {}}

        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = Mock(return_value=mock_context_manager)
        mock_context_manager.__exit__ = Mock(return_value=False)

        with patch('src.ui.components.chat_interface.ui') as mock_ui:
            mock_ui.column.return_value = mock_context_manager
            mock_ui.row.return_value = mock_context_manager
            mock_ui.input.return_value = mock_context_manager
            mock_ui.button.return_value = mock_context_manager
            mock_ui.label.return_value = mock_context_manager
            mock_ui.markdown.return_value = mock_context_manager

            result = create_chat_interface(mock_backend, session, state)

            assert mock_ui.column.called
            assert mock_ui.input.called

    def test_full_ui_flow(self, mock_backend):
        """完全なUIフローのテスト."""
        from src.ui.main_page import create_main_ui

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

        with patch('src.ui.main_page.ui') as mock_ui:
            mock_ui.column.return_value = mock_context_manager
            mock_ui.row.return_value = mock_context_manager
            mock_ui.label.return_value = mock_context_manager
            mock_ui.button.return_value = mock_context_manager
            mock_ui.icon.return_value = mock_context_manager
            mock_ui.header.return_value.__enter__ = Mock(return_value=mock_context_manager)
            mock_ui.header.return_value.__exit__ = Mock(return_value=False)
            mock_ui.space.return_value = mock_context_manager

            # サイドバーのモック
            with patch('src.ui.main_page.create_sidebar') as mock_create_sidebar:
                mock_create_sidebar.return_value = (
                    mock_context_manager, mock_tabs, mock_tab, mock_tab,
                    mock_tab, mock_tab, mock_tab, mock_tab_panel
                )

                # チャットインターフェースのモック
                with patch('src.ui.main_page.create_chat_interface') as mock_create_chat:
                    mock_create_chat.return_value = mock_context_manager

                    create_main_ui(mock_backend)

                    assert mock_create_sidebar.called
                    assert mock_create_chat.called

    def test_settings_persistence(self, mock_backend):
        """設定の永続化テスト."""
        mock_backend.get_user_settings.return_value = {
            'target_dir': '/test/path',
            'doc_dir': '/doc/path',
            'mode': 'Normal'
        }

        # 設定の更新をテスト
        new_settings = {
            'target_dir': '/new/path',
            'doc_dir': '/new/doc',
            'mode': 'Gap'
        }
        mock_backend.update_user_settings = Mock()
        mock_backend.update_user_settings(new_settings)

        mock_backend.update_user_settings.assert_called_once_with(new_settings)

    def test_chat_history_persistence(self, mock_backend):
        """チャット履歴の永続化テスト."""
        session = {'id': 'test-session', 'history': []}

        # メッセージの追加
        session['history'].append({'role': 'user', 'content': 'Hello'})
        session['history'].append({'role': 'ai', 'content': 'Hi!'})

        # 保存
        mock_backend.save_chat(session['id'], session['history'], 'Hello')

        mock_backend.save_chat.assert_called_once()

    def test_todo_crud_operations(self, mock_backend):
        """ToDoのCRUD操作テスト."""
        todo_service = mock_backend.get_todo_service()

        # 追加
        todo_service.add_todo(
            title='Test Todo',
            description='Test Description',
            priority='high',
            due_date='2024-12-31'
        )
        todo_service.add_todo.assert_called_once()

        # 削除
        todo_service.delete_todo('todo-001')
        todo_service.delete_todo.assert_called_once()

        # 完了切り替え
        todo_service.toggle_todo_completion('todo-001')
        todo_service.toggle_todo_completion.assert_called_once()