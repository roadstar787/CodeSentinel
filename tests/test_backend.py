import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from backend.core import RAGBackend

@pytest.fixture
def mock_backend():
    with patch('backend.core.OpenAIEmbeddings'), \
         patch('backend.core.FAISS'):
        backend = RAGBackend()
        backend.target_dir = "mock_target"
        backend.doc_dir = "mock_docs"
        return backend

def test_backend_init(mock_backend):
    assert mock_backend.stats["revision"].startswith("v")
    assert mock_backend.stats["total_chunks"] == 0

@patch('backend.core.TextLoader')
@patch('backend.core.RecursiveCharacterTextSplitter')
def test_rebuild_db_success(mock_splitter, mock_loader, mock_backend, temp_workspace):
    # セットアップ
    mock_backend.target_dir = str(temp_workspace)
    (temp_workspace / "test.py").write_text("print('test')", encoding='utf-8')
    
    # Loaderの動作をモック
    mock_doc = MagicMock()
    mock_doc.metadata = {}
    mock_loader.return_value.load.return_value = [mock_doc]
    
    # Splitterの動作をモック
    mock_splitter.return_value.split_documents.return_value = [mock_doc]
    
    # 実行
    with patch('backend.core.FAISS.from_documents') as mock_faiss_from:
        mock_faiss_from.return_value = MagicMock()
        success, msg = mock_backend.rebuild_db()
        
    assert success is True
    assert msg == "SUCCESS"
    assert mock_backend.stats["total_chunks"] > 0

def test_rebuild_db_no_files(mock_backend, temp_workspace):
    mock_backend.target_dir = str(temp_workspace)
    mock_backend.doc_dir = str(temp_workspace)
    # ファイルがない状態
    success, msg = mock_backend.rebuild_db()
    assert success is False
    assert msg == "No documents found"
