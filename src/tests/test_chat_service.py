"""ChatServiceのテスト"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.config.settings import Settings
from src.services.chat_service import ChatService


class TestChatService:
    """ChatServiceクラスのテスト"""

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
        config.paths.chat_dir_path = temp_dir / "chat_history"
        config.paths.chat_dir_path.mkdir(parents=True, exist_ok=True)
        config.lm_studio.url = "http://localhost:1234/v1"
        config.lm_studio.api_key = "lm-studio"
        config.lm_studio.check_embedding_ctx_length = False
        config.rag.temperature = 0.1
        return config

    def test_init(self, mock_config, temp_dir):
        """初期化のテスト"""
        with patch("src.services.chat_service.JsonRepository"):
            with patch("src.services.chat_service.FileStorageRepository"):
                service = ChatService(config=mock_config)
                assert service.config == mock_config
                assert service.chat_dir == temp_dir / "chat_history"

    @patch("src.services.chat_service.JsonRepository")
    @patch("src.services.chat_service.FileStorageRepository")
    def test_save_chat_history(self, mock_file_storage, mock_json_repo, mock_config, temp_dir):
        """チャット履歴保存のテスト"""
        mock_json_instance = Mock()
        mock_json_repo.return_value = mock_json_instance

        service = ChatService(config=mock_config)
        chat_id = "test-chat-123"
        messages = [{"role": "user", "content": "Hello"}]

        service.save_chat_history(chat_id, messages, title="Test Chat")

        # JSONリポジトリのsaveが呼ばれたことを確認
        mock_json_instance.save.assert_called_once()

    @patch("src.services.chat_service.JsonRepository")
    @patch("src.services.chat_service.FileStorageRepository")
    def test_load_chat_history(self, mock_file_storage, mock_json_repo, mock_config, temp_dir):
        """チャット履歴ロードのテスト"""
        mock_json_instance = Mock()
        mock_json_repo.return_value = mock_json_instance
        mock_json_instance.load.return_value = {
            "title": "Test Chat",
            "date": "2024-01-01 12:00:00",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        service = ChatService(config=mock_config)
        chat_id = "test-chat-123"
        result = service.load_chat_history(chat_id)

        mock_json_instance.load.assert_called_once()
        assert result is not None
        assert result["title"] == "Test Chat"

    @patch("src.services.chat_service.JsonRepository")
    @patch("src.services.chat_service.FileStorageRepository")
    def test_delete_chat_history(self, mock_file_storage, mock_json_repo, mock_config, temp_dir):
        """チャット履歴削除のテスト"""
        mock_json_instance = Mock()
        mock_json_repo.return_value = mock_json_instance
        mock_json_instance.delete.return_value = True

        service = ChatService(config=mock_config)
        chat_id = "test-chat-123"

        service.delete_chat_history(chat_id)

        mock_json_instance.delete.assert_called_once()

    @patch("src.services.chat_service.JsonRepository")
    @patch("src.services.chat_service.FileStorageRepository")
    def test_list_chat_histories(self, mock_file_storage, mock_json_repo, mock_config, temp_dir):
        """チャット履歴一覧取得のテスト"""
        mock_json_instance = Mock()
        mock_json_repo.return_value = mock_json_instance
        mock_json_instance.load.return_value = {
            "title": "Test Chat",
            "date": "2024-01-01 12:00:00",
            "messages": []
        }
        mock_file_storage_instance = Mock()
        mock_file_storage.return_value = mock_file_storage_instance
        mock_file_storage_instance.list_files.return_value = [
            str(temp_dir / "chat_history" / "chat1.json"),
            str(temp_dir / "chat_history" / "chat2.json")
        ]

        service = ChatService(config=mock_config)
        result = service.list_chat_histories()

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "chat1"
        assert result[0]["title"] == "Test Chat"

    def test_process_search_results(self, mock_config):
        """検索結果処理のテスト"""
        mock_docs = [
            Mock(metadata={"source": "file1.py", "type": "code"}),
            Mock(metadata={"source": "file2.md", "type": "document"}),
            Mock(metadata={"source": "file1.py", "type": "code"}),  # 重複
        ]

        with patch("src.services.chat_service.JsonRepository"):
            with patch("src.services.chat_service.FileStorageRepository"):
                service = ChatService(config=mock_config)
                result = service.process_search_results(mock_docs)

                assert len(result) == 2
                assert ("file1.py", "code") in result
                assert ("file2.md", "document") in result

    def test_format_context(self, mock_config):
        """コンテキストフォーマットのテスト"""
        mock_docs = [
            Mock(page_content="Content 1", metadata={"source": "file1.py", "type": "code"}),
            Mock(page_content="Content 2", metadata={"source": "file2.md", "type": "document"}),
        ]

        with patch("src.services.chat_service.JsonRepository"):
            with patch("src.services.chat_service.FileStorageRepository"):
                service = ChatService(config=mock_config)
                result = service.format_context(mock_docs)

                assert "TYPE: code" in result
                assert "FILE: file1.py" in result
                assert "Content 1" in result
                assert "TYPE: document" in result
                assert "FILE: file2.md" in result
                assert "Content 2" in result

    @patch("src.services.chat_service.ChatOpenAI")
    @pytest.mark.asyncio
    async def test_generate_response_normal(self, mock_chat_openai, mock_config):
        """通常モードの応答生成テスト"""
        mock_llm = AsyncMock()
        mock_chat_openai.return_value = mock_llm

        # ストリーミングレスポンスをシミュレート
        async def mock_astream(*args, **kwargs):
            for chunk in ["こんにちは", "、テストです。"]:
                yield chunk

        mock_chain = AsyncMock()
        mock_chain.astream = mock_astream

        with patch("src.services.chat_service.JsonRepository"):
            with patch("src.services.chat_service.FileStorageRepository"):
                with patch.object(ChatService, "create_prompt", return_value=Mock()):
                    with patch("src.services.chat_service.StrOutputParser", return_value=Mock()):
                        service = ChatService(config=mock_config)
                        service.llm = mock_llm

                        # create_promptとchainの設定をモック
                        service.create_prompt = Mock(return_value=Mock())
                        service.create_prompt.return_value.__or__ = Mock(return_value=Mock())
                        service.create_prompt.return_value.__or__.return_value.__or__ = Mock(return_value=mock_chain)

                        result = await service.generate_response("テスト", "コンテスト")

                        assert result["content"] == "こんにちは、テストです。"
                        assert result["gaps"] == []
                        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_generate_response_error(self, mock_config):
        """応答生成エラーのテスト"""
        with patch("src.services.chat_service.JsonRepository"):
            with patch("src.services.chat_service.FileStorageRepository"):
                service = ChatService(config=mock_config)
                service.create_prompt = Mock(side_effect=Exception("LLM Error"))

                result = await service.generate_response("テスト", "コンテスト")

                assert result["content"] == "Error: LLM Error"
                assert result["gaps"] == []
                assert result["success"] is False