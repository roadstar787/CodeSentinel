"""VectorStoreRepositoryのテスト"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.repositories.vector_store_repository import VectorStoreRepository


class TestVectorStoreRepository:
    """VectorStoreRepositoryクラスのテスト"""

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリの作成"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_config(self):
        """モック設定オブジェクトの作成"""
        config = Mock()
        config.lm_studio.url = "http://localhost:1234/v1"
        config.lm_studio.api_key = "lm-studio"
        config.lm_studio.check_embedding_ctx_length = False
        return config

    def test_init_with_mock(self, mock_config):
        """初期化のテスト"""
        with patch("src.repositories.vector_store_repository.OpenAIEmbeddings"):
            repository = VectorStoreRepository(config=mock_config)

            assert repository.config == mock_config
            assert repository.vectorstore is None

    @patch("src.repositories.vector_store_repository.OpenAIEmbeddings")
    @patch("src.repositories.vector_store_repository.FAISS")
    def test_load_local(self, mock_faiss_class, mock_embeddings_class, mock_config, temp_dir):
        """ローカルからのロードテスト"""
        db_path = str(temp_dir / "faiss_index")

        mock_faiss_instance = Mock()
        mock_faiss_class.load_local.return_value = mock_faiss_instance

        mock_embeddings_instance = Mock()
        mock_embeddings_class.return_value = mock_embeddings_instance

        repository = VectorStoreRepository.load_local(db_path, mock_config)

        mock_faiss_class.load_local.assert_called_once()
        assert repository.vectorstore is not None

    @patch("src.repositories.vector_store_repository.OpenAIEmbeddings")
    @patch("src.repositories.vector_store_repository.FAISS")
    def test_save_local(self, mock_faiss_class, mock_embeddings_class, mock_config, temp_dir):
        """ローカルへの保存テスト"""
        db_path = str(temp_dir / "faiss_index")

        mock_faiss_instance = Mock()
        mock_embeddings_instance = Mock()
        mock_embeddings_class.return_value = mock_embeddings_instance
        mock_faiss_class.return_value = mock_faiss_instance

        repository = VectorStoreRepository(config=mock_config)
        repository.vectorstore = mock_faiss_instance
        repository.save_local(db_path)

        mock_faiss_instance.save_local.assert_called_once_with(db_path)

    def test_as_retriever_with_vectorstore(self, mock_config):
        """リトリーバー取得テスト（ベクトルストアあり）"""
        with patch("src.repositories.vector_store_repository.OpenAIEmbeddings"):
            mock_vectorstore = Mock()
            mock_retriever = Mock()
            mock_vectorstore.as_retriever.return_value = mock_retriever

            repository = VectorStoreRepository(config=mock_config)
            repository.vectorstore = mock_vectorstore

            search_kwargs = {"k": 5}
            result = repository.as_retriever(search_kwargs=search_kwargs)

            mock_vectorstore.as_retriever.assert_called_once_with(search_kwargs=search_kwargs)
            assert result == mock_retriever

    def test_as_retriever_without_vectorstore(self, mock_config):
        """リトリーバー取得テスト（ベクトルストアなし）"""
        with patch("src.repositories.vector_store_repository.OpenAIEmbeddings"):
            repository = VectorStoreRepository(config=mock_config)

            result = repository.as_retriever()

            assert result is None

    def test_index_with_vectorstore(self, mock_config):
        """インデックス取得テスト（ベクトルストアあり）"""
        with patch("src.repositories.vector_store_repository.OpenAIEmbeddings"):
            mock_vectorstore = Mock()
            mock_index = Mock()
            mock_vectorstore.index = mock_index

            repository = VectorStoreRepository(config=mock_config)
            repository.vectorstore = mock_vectorstore

            assert repository.index == mock_index

    def test_index_without_vectorstore(self, mock_config):
        """インデックス取得テスト（ベクトルストアなし）"""
        with patch("src.repositories.vector_store_repository.OpenAIEmbeddings"):
            repository = VectorStoreRepository(config=mock_config)

            assert repository.index is None

    @patch("src.repositories.vector_store_repository.OpenAIEmbeddings")
    @patch("src.repositories.vector_store_repository.FAISS")
    def test_from_documents(self, mock_faiss_class, mock_embeddings_class, mock_config):
        """ドキュメントからのベクトルストア作成テスト"""
        from langchain_core.documents import Document

        mock_embeddings_instance = Mock()
        mock_embeddings_class.return_value = mock_embeddings_instance

        mock_vectorstore = Mock()
        mock_faiss_class.from_texts.return_value = mock_vectorstore

        documents = [
            Document(page_content="content1", metadata={"source": "test1.py"}),
            Document(page_content="content2", metadata={"source": "test2.py"}),
        ]

        repository = VectorStoreRepository.from_documents(documents, mock_config)

        mock_faiss_class.from_texts.assert_called_once()
        assert repository.vectorstore == mock_vectorstore

    @patch("src.repositories.vector_store_repository.OpenAIEmbeddings")
    @patch("src.repositories.vector_store_repository.FAISS")
    def test_from_documents_with_batching(self, mock_faiss_class, mock_embeddings_class, mock_config):
        """バッチ処理付きドキュメントからのベクトルストア作成テスト"""
        from langchain_core.documents import Document

        mock_embeddings_instance = Mock()
        mock_embeddings_class.return_value = mock_embeddings_instance

        mock_vectorstore = Mock()
        mock_faiss_class.from_texts.return_value = mock_vectorstore

        # 15件のドキュメントを作成（バッチサイズ10を超えてテスト）
        documents = [
            Document(page_content=f"content{i}", metadata={"source": f"test{i}.py"})
            for i in range(15)
        ]

        repository = VectorStoreRepository.from_documents(documents, mock_config)

        # 最初のバッチでfrom_textsが呼ばれる
        mock_faiss_class.from_texts.assert_called_once()
        # 残りのドキュメントでadd_textsが呼ばれる
        mock_vectorstore.add_texts.assert_called()
        assert repository.vectorstore == mock_vectorstore