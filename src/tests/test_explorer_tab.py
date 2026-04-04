"""エクスプローラータブのテスト"""

from collections import Counter
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest


class TestBuildTreeNodes:
    """ツリーノード構築ロジックのテスト."""

    def test_build_nodes_for_file(self):
        """ファイルのノード構築をテスト."""
        from src.ui.components.sidebar_tabs.explorer_tab import _build_nodes

        mock_path = Mock(spec=Path)
        mock_path.name = 'test.py'
        mock_path.is_file.return_value = True
        mock_path.is_dir.return_value = False
        mock_path.suffix = '.py'
        mock_path.relative_to.return_value = 'test.py'
        mock_path.iterdir.side_effect = PermissionError("Mock permission error")

        state = {'hit_counts': Counter()}
        node = _build_nodes(mock_path, Path('/test'), state, {'.py'})

        assert node['label'] == 'test.py'
        assert node['icon'] == 'description'
        assert 'children' not in node

    def test_build_nodes_for_directory(self, tmp_path):
        """ディレクトリのノード構築をテスト."""
        from src.ui.components.sidebar_tabs.explorer_tab import _build_nodes

        # テスト用のディレクトリ構造を作成
        sub_dir = tmp_path / 'subdir'
        sub_dir.mkdir()
        test_file = tmp_path / 'test.py'
        test_file.write_text('print("hello")')

        state = {'hit_counts': Counter()}
        node = _build_nodes(tmp_path, tmp_path, state, {'.py'})

        assert node['icon'] == 'folder'
        assert 'children' in node
        # 空のsubdirはスキップされ、test.pyのみが含まれる
        assert len(node['children']) == 1
        assert node['children'][0]['label'] == 'test.py'

    def test_build_nodes_skips_hidden_files(self, tmp_path):
        """隠しファイルをスキップすることをテスト."""
        from src.ui.components.sidebar_tabs.explorer_tab import _build_nodes

        hidden_file = tmp_path / '.hidden'
        hidden_file.write_text('hidden content')
        visible_file = tmp_path / 'visible.py'
        visible_file.write_text('print("hello")')

        state = {'hit_counts': Counter()}
        node = _build_nodes(tmp_path, tmp_path, state, {'.py'})

        assert len(node['children']) == 1
        assert node['children'][0]['label'] == 'visible.py'

    def test_build_nodes_filters_by_extension(self, tmp_path):
        """サポートされていない拡張子のファイルをスキップすることをテスト."""
        from src.ui.components.sidebar_tabs.explorer_tab import _build_nodes

        py_file = tmp_path / 'test.py'
        py_file.write_text('print("hello")')
        txt_file = tmp_path / 'test.txt'
        txt_file.write_text('text content')

        state = {'hit_counts': Counter()}
        node = _build_nodes(tmp_path, tmp_path, state, {'.py'})

        assert len(node['children']) == 1
        assert node['children'][0]['label'] == 'test.py'

    def test_build_nodes_with_hit_counts(self, tmp_path):
        """ヒットカウント付きのノード構築をテスト."""
        from src.ui.components.sidebar_tabs.explorer_tab import _build_nodes

        test_file = tmp_path / 'test.py'
        test_file.write_text('print("hello")')

        state = {'hit_counts': Counter({'test.py': 3})}
        node = _build_nodes(tmp_path, tmp_path, state, {'.py'})

        assert node['children'][0]['label'] == 'test.py • 3'
        assert 'background: rgba(99, 102, 241,' in node['children'][0]['style']

    def test_build_nodes_pdf_icon(self, tmp_path):
        """PDFファイルのアイコン設定をテスト."""
        from src.ui.components.sidebar_tabs.explorer_tab import _build_nodes

        pdf_file = tmp_path / 'document.pdf'
        pdf_file.write_text('pdf content')

        state = {'hit_counts': Counter()}
        node = _build_nodes(tmp_path, tmp_path, state, {'.pdf'})

        assert node['children'][0]['icon'] == 'picture_as_pdf'

    def test_build_nodes_excel_icon(self, tmp_path):
        """Excelファイルのアイコン設定をテスト."""
        from src.ui.components.sidebar_tabs.explorer_tab import _build_nodes

        xlsx_file = tmp_path / 'data.xlsx'
        xlsx_file.write_text('excel content')

        state = {'hit_counts': Counter()}
        node = _build_nodes(tmp_path, tmp_path, state, {'.xlsx'})

        assert node['children'][0]['icon'] == 'table_view'

    def test_build_nodes_pptx_icon(self, tmp_path):
        """PowerPointファイルのアイコン設定をテスト."""
        from src.ui.components.sidebar_tabs.explorer_tab import _build_nodes

        pptx_file = tmp_path / 'presentation.pptx'
        pptx_file.write_text('pptx content')

        state = {'hit_counts': Counter()}
        node = _build_nodes(tmp_path, tmp_path, state, {'.pptx'})

        assert node['children'][0]['icon'] == 'present_to_all'

    def test_build_nodes_md_icon(self, tmp_path):
        """Markdownファイルのアイコン設定をテスト."""
        from src.ui.components.sidebar_tabs.explorer_tab import _build_nodes

        md_file = tmp_path / 'readme.md'
        md_file.write_text('# README')

        state = {'hit_counts': Counter()}
        node = _build_nodes(tmp_path, tmp_path, state, {'.md'})

        assert node['children'][0]['icon'] == 'article'


class TestCreateExplorerTab:
    """エクスプローラータブ作成のテスト."""

    @pytest.fixture
    def mock_backend(self):
        """モックバックエンド."""
        backend = Mock()
        backend.get_user_settings.return_value = {
            'target_dir': '',
            'doc_dir': '',
        }
        return backend

    def test_create_explorer_tab_returns_column(self, mock_backend):
        """エクスプローラータブがcolumnを返すことをテスト."""
        from src.ui.components.sidebar_tabs.explorer_tab import create_explorer_tab

        with patch('src.ui.components.sidebar_tabs.explorer_tab.ui') as mock_ui:
            self._setup_mock_ui(mock_ui)

            result = create_explorer_tab(mock_backend, Mock(), Mock())

            assert result is not None

    def test_create_explorer_tab_with_preview_callback(self, mock_backend):
        """プレビューコールバック付きのエクスプローラータブをテスト."""
        from src.ui.components.sidebar_tabs.explorer_tab import create_explorer_tab

        mock_preview_open = Mock()

        with patch('src.ui.components.sidebar_tabs.explorer_tab.ui') as mock_ui:
            self._setup_mock_ui(mock_ui)

            create_explorer_tab(mock_backend, Mock(), mock_preview_open)

    def _setup_mock_ui(self, mock_ui):
        """UIモックを設定する."""
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = Mock(return_value=mock_context_manager)
        mock_context_manager.__exit__ = Mock(return_value=False)

        mock_ui.column.return_value = mock_context_manager
        mock_ui.label.return_value = mock_context_manager
        mock_ui.button.return_value = mock_context_manager
        mock_ui.row.return_value = mock_context_manager
        mock_ui.tree.return_value = MagicMock()
        mock_ui.tree.return_value.add_slot = Mock()