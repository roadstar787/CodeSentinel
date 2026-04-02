"""RAGバックエンドのテスト."""

import pytest

from src.config.settings import Settings
from src.core.backend import RAGBackend


class TestRAGBackend:
    """RAGバックエンドのテストクラス."""

    @pytest.fixture
    def backend(self):
        """RAGバックエンドのフィクスチャ."""
        config = Settings()
        return RAGBackend(config)

    def test_init(self, backend) -> None:
        """初期化のテスト."""
        assert backend.config is not None
        assert backend.mode == "Normal"
        assert backend.stats is not None
        assert backend.chat_service is not None
        assert backend.document_service is not None
        assert backend.todo_service is not None

    def test_get_chat_service(self, backend) -> None:
        """チャットサービス取得のテスト."""
        service = backend.get_chat_service()
        assert service is not None

    def test_get_todo_service(self, backend) -> None:
        """ToDoサービス取得のテスト."""
        service = backend.get_todo_service()
        assert service is not None

    def test_get_document_service(self, backend) -> None:
        """ドキュメントサービス取得のテスト."""
        service = backend.get_document_service()
        assert service is not None

    @pytest.mark.asyncio
    async def test_check_lm_studio(self, backend) -> None:
        """LM Studio接続確認のテスト."""
        result = await backend.check_lm_studio()
        assert isinstance(result, bool)

    def test_load_db(self, backend) -> None:
        """データベースロードのテスト."""
        result = backend.load_db()
        assert isinstance(result, bool)

    def test_get_retriever(self, backend) -> None:
        """リトリーバー取得のテスト."""
        result = backend.get_retriever()
        # ベクトルストアがロードされていない場合はNone
        assert result is None or hasattr(result, 'invoke')

    @pytest.mark.skip(reason="rebuild_dbは実際のファイル処理を行うため統合テストではスキップ")
    @pytest.mark.asyncio
    async def test_rebuild_db(self, backend) -> None:
        """データベース再構築のテスト."""
        success, message = await backend.rebuild_db()
        assert isinstance(success, bool)
        assert isinstance(message, str)

    def test_list_chats(self, backend) -> None:
        """チャット一覧取得のテスト."""
        result = backend.list_chats()
        assert isinstance(result, list)

    def test_load_chat(self, backend) -> None:
        """チャットロードのテスト."""
        result = backend.load_chat("nonexistent_id")
        assert result is None

    def test_save_chat(self, backend) -> None:
        """チャット保存のテスト."""
        messages = [{"role": "user", "content": "test"}]
        backend.save_chat("test_id", messages, "test_chat")
        # エラーが発生しなければテスト成功
        assert True

    def test_delete_chat(self, backend) -> None:
        """チャット削除のテスト."""
        backend.delete_chat("nonexistent_id")
        # エラーが発生しなければテスト成功
        assert True

    def test_update_user_settings(self, backend) -> None:
        """ユーザー設定更新のテスト."""
        user_storage = {"target_dir": "new_path", "mode": "Gap"}
        backend.update_user_settings(user_storage)
        assert backend.mode == "Gap"

    def test_get_user_settings(self, backend) -> None:
        """ユーザー設定取得のテスト."""
        result = backend.get_user_settings()
        assert isinstance(result, dict)
        assert "target_dir" in result
        assert "doc_dir" in result
        assert "mode" in result

    def test_sync_statistics(self, backend) -> None:
        """統計情報同期のテスト."""
        stats = backend.get_document_service().get_statistics()
        backend._sync_statistics()
        assert backend.stats["total_chunks"] == stats["total_chunks"]