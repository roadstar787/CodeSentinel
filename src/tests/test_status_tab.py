"""ステータスタブのテスト"""

from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pytest


class TestStatusTab:
    """ステータスタブのテスト."""

    @pytest.fixture
    def mock_backend(self):
        """モックバックエンド."""
        backend = Mock()

        mock_doc_service = Mock()
        mock_doc_service.get_statistics.return_value = {
            'total_chunks': 100,
            'vector_store_loaded': True,
            'lm_connected': False,
            'model': 'test-model',
        }
        backend.get_document_service.return_value = mock_doc_service
        # AsyncMockを使ってawaitに対応
        backend.check_lm_studio = AsyncMock()

        return backend

    def test_create_status_tab_returns_column(self, mock_backend):
        """ステータスタブがcolumnを返すことをテスト."""
        from src.ui.components.sidebar_tabs.status_tab import create_status_tab

        with patch('src.ui.components.sidebar_tabs.status_tab.ui') as mock_ui:
            mock_container = self._setup_mock_ui(mock_ui)
            mock_stats_labels: dict = {}

            result = create_status_tab(mock_backend, mock_stats_labels)

            assert result is not None

    def test_render_stats_initializes_labels(self, mock_backend):
        """統計表示がラベルを初期化することをテスト."""
        from src.ui.components.sidebar_tabs.status_tab import _render_stats

        mock_container = MagicMock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=False)

        mock_labels: dict = {}

        with patch('src.ui.components.sidebar_tabs.status_tab.ui') as mock_ui:
            mock_label = Mock()
            mock_ui.label.return_value = mock_label

            _render_stats(mock_container, mock_backend, mock_labels)

            assert 'chunks' in mock_labels
            assert 'vector' in mock_labels
            assert 'lm' in mock_labels
            assert 'model' in mock_labels

    def test_render_stats_displays_correct_values(self, mock_backend):
        """統計表示が正しい値を表示することをテスト."""
        from src.ui.components.sidebar_tabs.status_tab import _render_stats

        mock_container = MagicMock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=False)

        mock_labels: dict = {}

        with patch('src.ui.components.sidebar_tabs.status_tab.ui') as mock_ui:
            mock_label = Mock()
            mock_ui.label.return_value = mock_label

            _render_stats(mock_container, mock_backend, mock_labels)

            # 統計値が正しく設定されていることを確認
            mock_ui.label.assert_any_call('総チャンク数: 100')
            mock_ui.label.assert_any_call('ベクトルストア: ロード済み')
            mock_ui.label.assert_any_call('LM Studio: 未接続')
            mock_ui.label.assert_any_call('モデル: test-model')

    def test_update_stats_ui(self, mock_backend):
        """統計UI更新がラベルを更新することをテスト."""
        from src.ui.components.sidebar_tabs.status_tab import _update_stats_ui

        mock_stats_labels: dict = {
            'chunks': Mock(),
            'vector': Mock(),
            'lm': Mock(),
            'model': Mock(),
        }

        _update_stats_ui(mock_backend, mock_stats_labels)  # type: ignore[arg-type]

        # ラベルが更新されていることを確認
        mock_stats_labels['chunks'].set_text.assert_called_once()
        mock_stats_labels['vector'].set_text.assert_called_once()
        mock_stats_labels['lm'].set_text.assert_called_once()
        mock_stats_labels['model'].set_text.assert_called_once()

    def test_start_status_update_timer(self, mock_backend):
        """定期更新タイマーが設定されることをテスト."""
        from src.ui.components.sidebar_tabs.status_tab import _start_status_update_timer

        mock_stats_labels: dict = {}

        with patch('src.ui.components.sidebar_tabs.status_tab.ui') as mock_ui:
            _start_status_update_timer(mock_backend, mock_stats_labels)
            mock_ui.timer.assert_called_once()

    def _setup_mock_ui(self, mock_ui):
        """UIモックを設定する."""
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = Mock(return_value=mock_context_manager)
        mock_context_manager.__exit__ = Mock(return_value=False)

        mock_ui.column.return_value = mock_context_manager
        mock_ui.label.return_value = mock_context_manager
        mock_ui.row.return_value = mock_context_manager
        mock_ui.button.return_value = mock_context_manager
        mock_ui.timer.return_value = MagicMock()

        return mock_context_manager