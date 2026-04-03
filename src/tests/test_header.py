"""ヘッダーのテスト"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.ui.components.header import create_header


class TestHeader:
    """ヘッダーのテストクラス."""

    def test_create_header_returns_mode_toggle(self) -> None:
        """create_headerがモード切替を返すことをテスト."""
        with patch('src.ui.components.header.ui') as mock_ui:
            mock_toggle = Mock()
            mock_ui.toggle.return_value = mock_toggle
            
            result = create_header()
            assert mock_ui.toggle.called