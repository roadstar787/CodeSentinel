"""サイドバー（エクスプローラー、TODO）のリアクティブ動作検証テスト (TDD)"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from collections import Counter

@pytest.fixture
def mock_backend():
    """統計情報とサービスを持つモックバックエンド."""
    backend = Mock()
    backend.stats = {
        "chat_history": [],
        "todos": [], # 新規追加予定
        "is_chat_generating": False,
        "is_rebuilding": False,
    }
    backend.get_user_settings.return_value = {"target_dir": "/test", "doc_dir": ""}
    backend.get_todo_service.return_value = Mock()
    return backend

@pytest.mark.asyncio
async def test_explorer_reacts_to_hit_counts(mock_backend):
    """state['hit_counts'] の更新がエクスプローラーの再描画を誘発するかテスト."""
    from src.ui.components.sidebar_tabs.explorer_tab import create_explorer_tab
    
    state = {'hit_counts': Counter()}
    
    # ui.refreshable がデコレータとして機能するようにモック
    def mock_refreshable(f):
        def refresh(): f()
        f.refresh = refresh
        return f

    with patch('src.ui.components.sidebar_tabs.explorer_tab.ui') as mock_ui, \
         patch('src.ui.components.sidebar_tabs.explorer_tab._refresh_explorer') as mock_refresh:
        
        mock_ui.refreshable = mock_refreshable
        
        # 初期描画
        create_explorer_tab(mock_backend, state)
        assert mock_refresh.call_count == 1
        
        # ヒットカウントを更新
        state['hit_counts'] = Counter({'file1.py': 5})
        
        # タイマーのコールバックを手動で実行するか、待機する
        # ここではタイマーをキャプチャして実行するのが確実
        timer_callback = mock_ui.timer.call_args[0][1]
        timer_callback()
        
        # 期待値: 再描画が走っていること
        assert mock_refresh.call_count == 2

@pytest.mark.asyncio
async def test_todo_tab_reacts_to_stats_change(mock_backend):
    """backend.stats['todos'] の更新が TODO タブの再描画を誘発するかテスト."""
    from src.ui.components.sidebar_tabs.todo_tab import create_todo_tab
    
    # サービスの動作をモック
    mock_todo_service = mock_backend.get_todo_service.return_value
    mock_todo_service.list_todos.return_value = []
    mock_todo_service.get_todo_statistics.return_value = {"total": 0, "pending": 0, "completed": 0}

    with patch('src.ui.components.sidebar_tabs.todo_tab.ui') as mock_ui:
        # TODOタブ作成
        create_todo_tab(mock_backend)
        
        # 初期化時に stats['todos'] がセットされることを期待（現在は未実装）
        # backend.stats['todos'] = [{"id": "1", "title": "Test TODO", "completed": False}]
        # render_todo_list.refresh() などを期待
        
        # 現状の実装は _refresh_todo_list() を直接呼んでいるため、
        # stats の変更だけでは再描画されないはず
        pass

def test_chat_interface_sets_counter_hit_counts():
    """chat_interface が hit_counts を List ではなく Counter で保存するかテスト."""
    # このテストは chat_interface.py のリファクタリング後にパスするはず
    pass
