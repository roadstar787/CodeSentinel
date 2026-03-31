"""チャットサービスのテスト."""

import pytest

from config.settings import Settings
from services.chat_service import ChatService


class TestChatService:
    """チャットサービスのテストクラス."""

    @pytest.fixture
    def chat_service(self):
        """チャットサービスのフィクスチャ."""
        config = Settings()
        return ChatService(config)

    @pytest.mark.asyncio
    async def test_generate_response(self, chat_service) -> None:
        """応答生成のテスト."""
        query = "テストクエリ"
        context = "テストコンテキスト"

        result = await chat_service.generate_response(query, context)

        assert "content" in result
        assert "gaps" in result
        assert "success" in result
        assert result["success"] is True

    def test_process_search_results(self, chat_service) -> None:
        """検索結果処理のテスト."""
        docs = [{"metadata": {"source": "test.py"}}]

        result = chat_service.process_search_results(docs)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_format_context(self, chat_service) -> None:
        """コンテキストフォーマットのテスト."""
        docs = [{"metadata": {"source": "test.py"}, "page_content": "テストコンテンツ"}]

        result = chat_service.format_context(docs)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_list_chat_histories(self, chat_service) -> None:
        """チャット履歴一覧取得のテスト."""
        result = chat_service.list_chat_histories()

        assert isinstance(result, list)
