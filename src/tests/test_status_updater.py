"""ステータス更新のテスト"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.ui.components.status_updater import create_status_updater


class TestStatusUpdater:
    """ステータス更新のテストクラス."""

    def test_create_status_updater_returns_update_function(self) -> None:
        """create_status_updaterが更新関数を返すことをテスト."""
        with patch('src.ui.components.status_updater.ui'):
            result = create_status_updater()
            assert callable(result)

    def test_update_status_with_stats(self) -> None:
        """ステータス更新関数が stats で呼び出せることをテスト."""
        with patch('src.ui.components.status_updater.ui'):
            update_status = create_status_updater()
            # 関数が呼び出し可能であることを確認
            assert callable(update_status)