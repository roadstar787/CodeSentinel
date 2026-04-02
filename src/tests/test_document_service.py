"""ドキュメントサービスのテスト."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from src.config.settings import Settings
from src.services.document_service import DocumentService
from src.repositories.vector_store_repository import VectorStoreRepository


class TestDocumentService:
    """ドキュメントサービスのテストクラス."""

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリの作成"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_config(self, temp_dir):
        """モック設定オブジェクトの作成"""
        config = Settings()
        config.paths.target_dir = str(temp_dir / "target")
        config.paths.doc_dir = str(temp_dir / "docs")
        config.paths.db_path = str(temp_dir / "faiss_index")
        # db_full_pathはpropertyなのでdb_path経由で設定
        config.paths.chat_dir_path = temp_dir / "chat_history"
        config.paths.todo_dir_path = temp_dir / "todo_history"
        config.paths.chat_dir_path.mkdir(parents=True, exist_ok=True)
        config.paths.todo_dir_path.mkdir(parents=True, exist_ok=True)
        config.lm_studio.url = "http://localhost:1234/v1"
        config.lm_studio.api_key = "lm-studio"
        config.lm_studio.check_embedding_ctx_length = False
        config.rag.search_k = 10
        return config

    def test_init(self, mock_config):
        """初期化のテスト"""
        service = DocumentService(config=mock_config)

        assert service.config == mock_config
        assert service.vector_store is None
        assert service.stats["total_chunks"] == 0

    @patch.object(VectorStoreRepository, "load_local")
    def test_load_database_success(self, mock_load_local, mock_config, temp_dir):
        """データベースロード成功のテスト"""
        mock_vector_store_instance = Mock()
        mock_load_local.return_value = mock_vector_store_instance

        service = DocumentService(config=mock_config)
        result = service.load_database()

        assert result is True
        assert service.vector_store == mock_vector_store_instance

    @patch.object(VectorStoreRepository, "load_local")
    def test_load_database_file_not_found(self, mock_load_local, mock_config, temp_dir):
        """データベースファイルが見つからないテスト"""
        mock_load_local.side_effect = FileNotFoundError()

        service = DocumentService(config=mock_config)
        result = service.load_database()

        assert result is False
        assert service.vector_store is None

    def test_get_retriever_with_vector_store(self, mock_config):
        """ベクトルストアありのリトリーバー取得テスト"""
        mock_vector_store_instance = Mock()
        mock_retriever = Mock()
        mock_vector_store_instance.as_retriever.return_value = mock_retriever

        service = DocumentService(config=mock_config)
        service.vector_store = mock_vector_store_instance

        result = service.get_retriever()

        mock_vector_store_instance.as_retriever.assert_called_once()
        assert result == mock_retriever

    def test_get_retriever_without_vector_store(self, mock_config):
        """ベクトルストアなしのリトリーバー取得テスト"""
        service = DocumentService(config=mock_config)

        result = service.get_retriever()

        assert result is None

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_check_lm_studio_success(self, mock_client_class, mock_config):
        """LM Studio接続成功のテスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "test-model"}]}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        service = DocumentService(config=mock_config)
        result = await service.check_lm_studio()

        assert result is True
        assert service.stats["lm_connected"] is True
        assert service.stats["model"] == "test-model"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_check_lm_studio_failure(self, mock_client_class, mock_config):
        """LM Studio接続失敗のテスト"""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        service = DocumentService(config=mock_config)
        result = await service.check_lm_studio()

        assert result is False
        assert service.stats["lm_connected"] is False

    def test_get_statistics(self, mock_config):
        """統計情報取得のテスト"""
        service = DocumentService(config=mock_config)
        service.stats["total_chunks"] = 100
        service.stats["last_rebuild"] = "2024-01-01"

        result = service.get_statistics()

        assert result["total_chunks"] == 100
        assert result["last_rebuild"] == "2024-01-01"

    def test_update_statistics(self, mock_config):
        """統計情報更新のテスト"""
        service = DocumentService(config=mock_config)

        test_stats = {"total_chunks": 50, "model": "test-model"}
        service.update_statistics(test_stats)

        assert service.stats["total_chunks"] == 50
        assert service.stats["model"] == "test-model"

    @pytest.mark.asyncio
    @patch.object(VectorStoreRepository, "from_documents")
    @patch("src.services.document_service.DocumentProcessor")
    async def test_rebuild_database_success(self, mock_processor_class, mock_from_documents, mock_config, temp_dir):
        """データベース再構築成功のテスト"""
        from src.services.document_processor import ProcessedDocument

        # ディレクトリを作成
        target_dir = temp_dir / "target"
        target_dir.mkdir(parents=True, exist_ok=True)
        mock_config.paths.target_dir = str(target_dir)

        mock_processor_instance = Mock()
        mock_processor_instance.process_all_documents = AsyncMock(return_value=(True, "Processed 10 documents"))
        mock_processor_instance.get_processed_documents.return_value = [
            ProcessedDocument(content="test", metadata={"source": "test.py"})
        ]
        mock_processor_class.return_value = mock_processor_instance

        mock_vector_store_instance = Mock()
        mock_from_documents.return_value = mock_vector_store_instance

        service = DocumentService(config=mock_config)
        success, message = await service.rebuild_database()

        assert success is True
        assert service.vector_store == mock_vector_store_instance

    @pytest.mark.asyncio
    @patch("src.services.document_service.DocumentProcessor")
    async def test_rebuild_database_no_documents(self, mock_processor_class, mock_config):
        """データベース再構築失敗（ドキュメントなし）のテスト"""
        mock_processor_instance = Mock()
        mock_processor_instance.process_all_documents = AsyncMock(return_value=(False, "No documents found"))
        mock_processor_class.return_value = mock_processor_instance

        service = DocumentService(config=mock_config)
        success, message = await service.rebuild_database()

        assert success is False
        assert "No documents found" in message

    @pytest.mark.asyncio
    @patch("src.services.document_service.DocumentProcessor")
    async def test_rebuild_database_too_many_chunks(self, mock_processor_class, mock_config):
        """データベース再構築失敗（チャンク数過多）のテスト"""
        mock_processor_instance = Mock()
        mock_processor_instance.process_all_documents = AsyncMock(
            return_value=(False, "Too many document chunks (60000)")
        )
        mock_processor_class.return_value = mock_processor_instance

        service = DocumentService(config=mock_config)
        success, message = await service.rebuild_database()

        assert success is False
        assert "Too many document chunks" in message