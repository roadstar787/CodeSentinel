"""ドキュメントサービスのテスト."""

import pytest

from config.settings import Settings
from services.document_service import DocumentService


class TestDocumentService:
    """ドキュメントサービスのテストクラス."""

    @pytest.fixture
    def document_service(self):
        """ドキュメントサービスのフィクスチャ."""
        config = Settings()
        return DocumentService(config)

    @pytest.mark.asyncio
    async def test_rebuild_database(self, document_service) -> None:
        """データベース再構築のテスト."""
        success, message = await document_service.rebuild_database()

        assert success is True
        assert isinstance(message, str)

    def test_load_database(self, document_service) -> None:
        """データベースロードのテスト."""
        result = document_service.load_database()

        assert result is True

    def test_get_retriever(self, document_service) -> None:
        """リトリーバー取得のテスト."""
        result = document_service.get_retriever()

        assert result is None

    @pytest.mark.asyncio
    async def test_check_lm_studio(self, document_service) -> None:
        """LM Studio接続確認のテスト."""
        result = await document_service.check_lm_studio()

        assert result is True

    def test_get_statistics(self, document_service) -> None:
        """統計情報取得のテスト."""
        result = document_service.get_statistics()

        assert "total_chunks" in result
        assert isinstance(result["total_chunks"], int)

    def test_update_statistics(self, document_service) -> None:
        """統計情報更新のテスト."""
        test_stats = {"total_chunks": 10}
        document_service.update_statistics(test_stats)

        # エラーが発生しなければテスト成功
        assert True
