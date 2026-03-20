import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from ui.components.preview import PreviewDialog

@pytest.fixture
def mock_preview():
    with patch('ui.components.preview.ui'):
        # ui.timer などの呼び出しを回避
        dialog = PreviewDialog()
        return dialog

def test_apply_fix_success(mock_preview, temp_workspace):
    # セットアップ
    test_file = temp_workspace / "test.txt"
    test_file.write_text("old content", encoding='utf-8')
    
    # 状態のセットアップ
    mock_preview.search_state['file_path'] = test_file
    mock_preview.search_state['fix_code'] = "new content"
    
    # ダイアログのモック
    mock_diag = MagicMock()
    
    # 実行 (open, os.fsync などをモックせずに実際に一時ファイルでテスト)
    with patch('ui.components.preview.ui.notify'), \
         patch.object(mock_preview, 'open'): # プレビュー再読込はモック
        mock_preview.apply_fix(mock_diag)
    
    # 検証
    assert test_file.read_text(encoding='utf-8') == "new content"
    mock_diag.close.assert_called_once()

def test_apply_fix_no_code(mock_preview):
    mock_preview.search_state['file_path'] = Path("test.txt")
    mock_preview.search_state['fix_code'] = None
    
    mock_diag = MagicMock()
    with patch('ui.components.preview.ui.notify') as mock_notify:
        mock_preview.apply_fix(mock_diag)
        
    mock_notify.assert_called_with("No fix code available.", color='warning')
    mock_diag.close.assert_not_called()
