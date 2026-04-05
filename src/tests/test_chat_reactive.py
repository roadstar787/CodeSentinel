"""チャットインターフェースのリアクティブ化テスト (Test-First)"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# テスト対象
# リファクタリング前なので一旦インポートできるか確認
try:
    from src.ui.components.chat_interface import _handle_query
except ImportError:
    pass

class TestChatReactive:
    """チャットインターフェースのリアクティブ動作テスト."""

    @pytest.fixture
    def mock_backend(self):
        """統計情報を持つモックバックエンド."""
        backend = Mock()
        backend.stats = {
            "chat_history": [],
            "streaming_content": "",
            "is_chat_generating": False,
            "status_text": "",
            "last_notification": None
        }
        backend.get_retriever.return_value = Mock()
        backend.get_chat_service.return_value = Mock()
        backend.config = Mock()
        backend.config.paths.get_target_dir.return_value = "/test/target"
        backend.config.paths.get_doc_dir.return_value = "/test/doc"
        backend.mode = "Normal"
        return backend

    @pytest.mark.asyncio
    async def test_handle_query_updates_state_only(self, mock_backend):
        """クエリ処理がUIを直接触らず、状態（stats）のみを更新することをテスト."""
        from src.ui.components.chat_interface import _handle_query
        
        # モックUI要素
        mock_input_field = Mock()
        mock_input_field.value = "Hello AI"
        mock_chat_results = Mock() # 今回のリビルドでは直接触らないはず
        mock_state = {"hit_counts": []}
        
        # サービスの動作をモック
        mock_retriever = mock_backend.get_retriever.return_value
        mock_retriever.invoke.return_value = []
        
        mock_chat_service = mock_backend.get_chat_service.return_value
        mock_chat_service.process_search_results.return_value = []
        mock_chat_service.format_context.return_value = "Test Context"
        
        # 非同期生成部分をモック（今回は副作用のみを確認）
        with patch("src.ui.components.chat_interface._generate_response_async", new_callable=AsyncMock) as mock_gen, \
             patch("src.ui.components.chat_interface.ui") as mock_ui, \
             patch("src.ui.components.chat_interface.app") as mock_app:
            # 実行 (Async)
            await _handle_query(
                session={"id": "test-id", "history": []},
                input_field=mock_input_field,
                chat_results=mock_chat_results,
                state=mock_state,
                backend=mock_backend
            )
            
            # 検証: ユーザー入力が履歴 (stats) に追加されているか
            assert len(mock_backend.stats["chat_history"]) > 0
            assert mock_backend.stats["chat_history"][0]["role"] == "user"
            assert mock_backend.stats["chat_history"][0]["content"] == "Hello AI"
            
            # 検証: 生成中フラグがセットされているか
            assert mock_backend.stats["is_chat_generating"] is True

    @pytest.mark.asyncio
    async def test_generate_response_updates_final_state(self, mock_backend):
        """回答生成完了時に、最終的な回答がステートに追加されることをテスト."""
        from src.ui.components.chat_interface import _generate_response_async
        
        # 準備
        mock_backend.stats["chat_history"] = [{"role": "user", "content": "Hello"}]
        mock_backend.stats["is_chat_generating"] = True
        
        mock_chat_service = mock_backend.get_chat_service.return_value
        mock_chat_service.generate_response = AsyncMock(return_value={
            "content": "Hi there!",
            "success": True,
            "gaps": []
        })
        
        # 実行
        await _generate_response_async(
            query="Hello",
            context="Context",
            md=Mock(),           # 旧設計互換（削除予定）
            source_row=Mock(),   # 旧設計互換（削除予定）
            session={"id": "id", "history": []},
            chat_results=Mock(), # 旧設計互換（削除予定）
            backend=mock_backend,
            unique_hits=[]
        )
        
        # 検証
        assert len(mock_backend.stats["chat_history"]) == 2
        assert mock_backend.stats["chat_history"][1]["role"] == "ai"
        assert mock_backend.stats["chat_history"][1]["content"] == "Hi there!"
        assert mock_backend.stats["is_chat_generating"] is False
