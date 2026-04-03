"""プレビューダイアログのテスト"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.ui.components.preview_dialog import create_preview_dialog


class TestPreviewDialog:
    """プレビューダイアログのテストクラス."""

    def test_create_preview_dialog_returns_tuple(self) -> None:
        """create_preview_dialogが(get_dialog, open_preview)のタプルを返すことをテスト."""
        with patch('src.ui.components.preview_dialog.ui'), \
             patch('src.ui.components.preview_dialog.ui.dialog'), \
             patch('src.ui.components.preview_dialog.ui.card'):
            result = create_preview_dialog()
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert callable(result[0])  # get_dialog
            assert callable(result[1])  # open_preview

    def test_open_preview_with_empty_path(self) -> None:
        """空のパスを指定した場合のテスト."""
        with patch('src.ui.components.preview_dialog.ui.dialog'), \
             patch('src.ui.components.preview_dialog.ui.card'), \
             patch('src.ui.components.preview_dialog.ui.notify') as mock_notify:
            get_dialog_func, open_preview_func = create_preview_dialog()
            open_preview_func('', '.', None)
            mock_notify.assert_not_called()