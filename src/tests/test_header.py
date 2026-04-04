"""ヘッダーのテスト"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.ui.components.header import create_header


class TestHeader:
    """ヘッダーのテストクラス."""

    def test_create_header_renders_correctly(self) -> None:
        """create_headerが正しくレンダリングされることをテスト."""
        with patch('src.ui.components.header.ui') as mock_ui:
            # コンテキストマネージャーをサポートするモック
            mock_header = MagicMock()
            mock_header.__enter__ = Mock(return_value=mock_header)
            mock_header.__exit__ = Mock(return_value=None)
            mock_ui.header.return_value = mock_header
            mock_ui.header.return_value.classes.return_value = mock_header
            
            create_header()
            assert mock_ui.header.called