"""UIイベントハンドラのテスト"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path

from src.ui.handlers.event_handlers import EventHandlers


class TestEventHandlers:
    """イベントハンドラのテストクラス."""

    @pytest.fixture
    def mock_backend(self):
        """モックバックエンド."""
        backend = Mock()
        backend.mode = 'Normal'
        backend.list_chats.return_value = []
        backend.load_chat.return_value = None
        backend.delete_chat = Mock()
        backend.update_user_settings = Mock()

        mock_config = Mock()
        mock_config.paths.get_target_dir.return_value = Path('/target')
        mock_config.paths.get_doc_dir.return_value = Path('/docs')
        backend.config = mock_config

        backend.get_chat_service.return_value = Mock()
        backend.get_todo_service.return_value = Mock()

        return backend

    @pytest.fixture
    def mock_preview_func(self):
        """モックプレビュー関数."""
        return Mock()

    @pytest.fixture
    def mock_refresh_func(self):
        """モックリフレッシュ関数."""
        return Mock()

    @pytest.fixture
    def handlers(self, mock_backend, mock_preview_func, mock_refresh_func):
        """イベントハンドラインスタンス."""
        return EventHandlers(mock_backend, mock_preview_func, mock_refresh_func)

    def test_init(self, handlers, mock_backend, mock_preview_func, mock_refresh_func):
        """初期化のテスト."""
        assert handlers.backend == mock_backend
        assert handlers.preview_open == mock_preview_func
        assert handlers.refresh_explorer_func == mock_refresh_func

    def test_change_mode(self, handlers, mock_backend):
        """モード変更のテスト."""
        handlers.change_mode('Gap')
        assert mock_backend.mode == 'Gap'
        mock_backend.update_user_settings.assert_called_once_with({'mode': 'Gap'})

    def test_save_settings(self, handlers, mock_backend, mock_refresh_func):
        """設定保存のテスト."""
        with patch('src.ui.handlers.event_handlers.ui.notify') as mock_notify:
            handlers.save_settings('/new/target', '/new/docs')
            mock_backend.update_user_settings.assert_called_once()
            mock_refresh_func.assert_called_once()
            mock_notify.assert_called_once()

    def test_start_new_chat(self, handlers):
        """新しいチャット開始のテスト."""
        session = {'id': 'old-id', 'history': []}
        chat_results = Mock()
        chat_list_container = Mock()

        with patch('src.ui.handlers.event_handlers.ui.notify') as mock_notify:
            handlers.start_new_chat(session, chat_results, chat_list_container)
            assert session['id'] != 'old-id'
            assert session['history'] == []
            chat_results.clear.assert_called_once()
            mock_notify.assert_called_once()

    def test_delete_chat_session_current(self, handlers, mock_backend):
        """現在のチャット削除のテスト."""
        session = {'id': 'test-id', 'history': []}
        chat_results = Mock()
        chat_list_container = Mock()

        with patch.object(handlers, 'start_new_chat') as mock_start:
            handlers.delete_chat_session('test-id', session, chat_results, chat_list_container)
            mock_backend.delete_chat.assert_called_once_with('test-id')
            mock_start.assert_called_once()

    def test_delete_chat_session_other(self, handlers, mock_backend):
        """他のチャット削除のテスト."""
        session = {'id': 'test-id', 'history': []}
        chat_results = Mock()
        chat_list_container = Mock()

        with patch.object(handlers, 'refresh_chat_list') as mock_refresh:
            handlers.delete_chat_session('other-id', session, chat_results, chat_list_container)
            mock_backend.delete_chat.assert_called_once_with('other-id')
            mock_refresh.assert_called_once()

    def test_load_chat_session_no_data(self, handlers, mock_backend):
        """データなしの場合のチャットロードテスト."""
        mock_backend.load_chat.return_value = None
        session = {'id': 'old', 'history': []}
        chat_results = Mock()
        chat_list_container = Mock()

        handlers.load_chat_session(session, 'test-id', chat_results, chat_list_container)
        assert session['id'] == 'old'  # セッションが更新されていない

    def test_refresh_chat_list_empty(self, handlers, mock_backend):
        """空のチャットリストのテスト."""
        mock_backend.list_chats.return_value = []
        session = {'id': 'test'}
        chat_results = Mock()
        chat_list_container = Mock()

        with patch('src.ui.handlers.event_handlers.ui.label') as mock_label, \
             patch('src.ui.handlers.event_handlers.ui.row'):
            handlers.refresh_chat_list(session, chat_results, chat_list_container)
            chat_list_container.clear.assert_called_once()
            mock_label.assert_called_once()
