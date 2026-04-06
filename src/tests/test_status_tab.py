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

        mock_backend.stats = {'revision': 'v1.0'}
        mock_backend.document_service = Mock()
        mock_backend.document_service.vector_store = Mock()

        with patch('src.ui.components.sidebar_tabs.status_tab.ui') as mock_ui:
            mock_label = Mock()
            mock_ui.label.return_value = mock_label
            mock_ui.row.return_value.__enter__ = Mock(return_value=mock_container)
            mock_ui.row.return_value.__exit__ = Mock(return_value=False)
            mock_ui.row.return_value.classes.return_value = mock_container

            _render_stats(mock_container, mock_backend, mock_labels)

            assert 'total_chunks' in mock_labels
            assert 'vector_store' in mock_labels
            assert 'lm_status' in mock_labels
            assert 'lm_model' in mock_labels

    def test_render_stats_displays_correct_values(self, mock_backend):
        """統計表示が正しい値を表示することをテスト."""
        from src.ui.components.sidebar_tabs.status_tab import _render_stats

        mock_container = MagicMock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=False)

        mock_labels: dict = {}

        mock_backend.stats = {'revision': 'v1.0', 'total_chunks': 100}
        mock_backend.document_service = Mock()
        mock_backend.document_service.vector_store = Mock()

        with patch('src.ui.components.sidebar_tabs.status_tab.ui') as mock_ui:
            mock_label = Mock()
            mock_ui.label.return_value = mock_label
            mock_ui.row.return_value.__enter__ = Mock(return_value=mock_container)
            mock_ui.row.return_value.__exit__ = Mock(return_value=False)
            mock_ui.row.return_value.classes.return_value = mock_container

            # スキーマに沿ったキーでラベルが作成されることを確認
            _render_stats(mock_container, mock_backend, mock_labels)

            assert 'total_chunks' in mock_labels
            assert 'vector_store' in mock_labels
            assert 'lm_status' in mock_labels
            assert 'lm_model' in mock_labels
            assert 'cpu' in mock_labels
            assert 'ram' in mock_labels

    def test_update_stats_ui(self, mock_backend):
        """統計UI更新がラベルを更新することをテスト."""
        from src.ui.components.sidebar_tabs.status_tab import _update_stats_ui

        mock_stats_labels: dict = {
            'total_chunks': Mock(),
            'vector_store': Mock(),
            'lm_status': Mock(),
            'lm_model': Mock(),
            'cpu': Mock(),
            'ram': Mock(),
            'last_rebuild': Mock(),
        }

        mock_backend.stats = {
            'total_chunks': 100,
            'lm_connected': True,
            'model': 'test-model',
            'last_rebuild': '2024-01-01',
        }
        mock_backend.document_service = Mock()
        mock_backend.document_service.vector_store = Mock()

        with patch('src.ui.components.sidebar_tabs.status_tab.psutil') as mock_psutil:
            mock_psutil.cpu_percent.return_value = 25.0
            mock_psutil.virtual_memory.return_value = Mock(used=4 * 1024**3, total=16 * 1024**3)

            _update_stats_ui(mock_backend, mock_stats_labels)  # type: ignore[arg-type]

            # ラベルが更新されていることを確認
            mock_stats_labels['total_chunks'].set_text.assert_called_once_with('100')
            mock_stats_labels['cpu'].set_text.assert_called_once_with('25.0%')
            mock_stats_labels['lm_status'].set_text.assert_called_once_with('ONLINE')
            mock_stats_labels['lm_model'].set_text.assert_called_once_with('test-model')

    def test_status_update_timer_is_configured(self, mock_backend):
        """定期更新タイマーが設定されることをテスト."""
        from src.ui.components.sidebar_tabs.status_tab import create_status_tab

        mock_stats_labels: dict = {}

        with patch('src.ui.components.sidebar_tabs.status_tab.ui') as mock_ui:
            mock_container = MagicMock()
            mock_ui.column.return_value = mock_container
            mock_ui.row.return_value.__enter__ = Mock(return_value=mock_container)
            mock_ui.row.return_value.__exit__ = Mock(return_value=False)
            mock_ui.row.return_value.classes.return_value = mock_container
            mock_label = Mock()
            mock_ui.label.return_value = mock_label
            mock_backend.stats = {'revision': 'v1.0'}
            mock_backend.document_service = Mock()
            mock_backend.document_service.vector_store = Mock()

            create_status_tab(mock_backend, mock_stats_labels)
            # 3秒ごとのタイマーが設定されていることを確認
            mock_ui.timer.assert_called()

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