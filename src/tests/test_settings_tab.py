"""設定タブのテスト"""

from unittest.mock import Mock, patch, MagicMock
import pytest


class TestSettingsTab:
    """設定タブのテスト."""

    @pytest.fixture
    def mock_backend(self):
        """モックバックエンド."""
        backend = Mock()
        backend.get_user_settings.return_value = {
            'target_dir': '/test/target',
            'doc_dir': '/test/doc',
            'mode': 'Normal',
        }
        backend.update_user_settings.return_value = None

        mock_doc_service = Mock()
        mock_doc_service.get_statistics.return_value = {
            'total_chunks': 100,
            'vector_store_loaded': True,
            'lm_connected': False,
            'model': 'test-model',
        }
        backend.get_document_service.return_value = mock_doc_service

        return backend

    def test_create_settings_tab_returns_column(self, mock_backend):
        """設定タブがcolumnを返すことをテスト."""
        from src.ui.components.sidebar_tabs.settings_tab import create_settings_tab

        with patch('src.ui.components.sidebar_tabs.settings_tab.ui') as mock_ui:
            mock_container = self._setup_mock_ui(mock_ui)
            mock_stats_labels: dict = {}

            result = create_settings_tab(mock_backend, mock_stats_labels)  # type: ignore[arg-type]

            assert result is not None

    def test_save_settings(self, mock_backend):
        """設定保存をテスト."""
        from src.ui.components.sidebar_tabs.settings_tab import _save_settings

        mock_target_input = Mock()
        mock_target_input.value = '/new/target'
        mock_doc_input = Mock()
        mock_doc_input.value = '/new/doc'

        with patch('src.ui.components.sidebar_tabs.settings_tab.app') as mock_app:
            mock_app.storage.user = {}

            _save_settings(mock_backend, mock_target_input, mock_doc_input)

            mock_backend.update_user_settings.assert_called_once()
            call_args = mock_backend.update_user_settings.call_args[0][0]
            assert call_args['target_dir'] == '/new/target'
            assert call_args['doc_dir'] == '/new/doc'

    def test_rebuild_database_success(self, mock_backend):
        """データベース再構築成功をテスト."""
        import asyncio
        from src.ui.components.sidebar_tabs.settings_tab import _rebuild_database

        mock_backend.rebuild_db.return_value = (True, 'Success')

        async def run_test() -> None:
            with patch('src.ui.components.sidebar_tabs.settings_tab.ui') as mock_ui:
                mock_notify = Mock()
                mock_ui.notify = mock_notify
                # モックUI要素を作成
                mock_rebuild_button = Mock()
                mock_cancel_button = Mock()
                mock_progress_label = Mock()
                mock_progress_spinner = Mock()
                await _rebuild_database(
                    mock_backend, mock_rebuild_button, mock_cancel_button,
                    mock_progress_label, mock_progress_spinner, {}
                )
                mock_backend.rebuild_db.assert_called_once()

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(run_test())

    def test_rebuild_database_failure(self, mock_backend):
        """データベース再構築失敗をテスト."""
        import asyncio
        from src.ui.components.sidebar_tabs.settings_tab import _rebuild_database

        mock_backend.rebuild_db.return_value = (False, 'No models loaded')

        async def run_test() -> None:
            with patch('src.ui.components.sidebar_tabs.settings_tab.ui') as mock_ui:
                mock_notify = Mock()
                mock_ui.notify = mock_notify
                # モックUI要素を作成
                mock_rebuild_button = Mock()
                mock_cancel_button = Mock()
                mock_progress_label = Mock()
                mock_progress_spinner = Mock()
                await _rebuild_database(
                    mock_backend, mock_rebuild_button, mock_cancel_button,
                    mock_progress_label, mock_progress_spinner, {}
                )
                assert mock_notify.call_count >= 1

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(run_test())

    def test_update_stats_labels(self, mock_backend):
        """統計情報ラベルの更新をテスト."""
        from src.ui.components.sidebar_tabs.settings_tab import _update_stats_labels

        mock_stats_labels: dict = {
            'chunks': Mock(),
            'vector': Mock(),
            'lm': Mock(),
            'model': Mock(),
        }

        _update_stats_labels(mock_backend, mock_stats_labels)  # type: ignore[arg-type]

        # 統計ラベルが更新されていることを確認
        mock_stats_labels['chunks'].set_text.assert_called_once()
        mock_stats_labels['vector'].set_text.assert_called_once()

    def _setup_mock_ui(self, mock_ui):
        """UIモックを設定する."""
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = Mock(return_value=mock_context_manager)
        mock_context_manager.__exit__ = Mock(return_value=False)

        mock_ui.column.return_value = mock_context_manager
        mock_ui.label.return_value = mock_context_manager
        mock_ui.button.return_value = mock_context_manager
        mock_ui.row.return_value = mock_context_manager
        mock_ui.input.return_value = mock_context_manager
        mock_ui.spinner.return_value = mock_context_manager

        return mock_context_manager