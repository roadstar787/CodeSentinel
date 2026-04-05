"""RAG Backendの基本クラス
CodeSentinelのRAG機能の基底クラスを定義します。
サービスオーケストレーターとして各サービスを管理します。.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional, Union

from src.config.settings import Settings
from src.services.chat_service import ChatService
from src.services.document_service import DocumentService
from src.services.todo_service import TodoService


class RAGBackend:
    """RAG（Retrieval-Augmented Generation）のバックエンド処理を管理するクラス
    サービスオーケストレーターとして各サービスを連携させます.
    """

    def __init__(self, config: Optional[Settings] = None):
        """初期化.

        Args:
            config: 設定オブジェクト。Noneの場合はデフォルト設定を使用

        """
        self.config: Settings = config or Settings()
        self.mode: str = self.config.app.mode

        # サービスの初期化
        self.chat_service: ChatService = ChatService(self.config)
        self.document_service: DocumentService = DocumentService(self.config)
        self.todo_service: TodoService = TodoService(self.config.paths.todo_dir_path)

        # 統計情報（ドキュメントサービスから取得）
        self.stats: Dict[str, Any] = {
            "total_chunks": 0,
            "is_rebuilding": False,
            "status_text": "",
            "last_notification": None,  # Optional[Dict[str, str]]
            "chat_history": [],         # List[Dict[str, Any]]
            "streaming_content": "",    # Real-time response chunk
            "is_chat_generating": False,
            "lm_connected": False,
            "model": "N/A",
            "revision": "v0.4.0",
            "last_rebuild": "Never"
        }

        # 再構築キャンセルフラグ
        self._rebuild_cancel_event: asyncio.Event = asyncio.Event()

        # 初期化
        self._initialize_directories()
        self._initialize_services()

    def _initialize_directories(self) -> None:
        """必要なディレクトリの初期化."""
        # チャット履歴ディレクトリ
        self.config.paths.chat_dir.mkdir(exist_ok=True)

        # ベクトルストアディレクトリ
        self.config.paths.db_full_path.mkdir(exist_ok=True)

    def _initialize_services(self) -> None:
        """サービスを初期化."""
        # 統計情報を同期
        self._sync_statistics()

    def _sync_statistics(self) -> None:
        """統計情報を同期."""
        doc_stats = self.document_service.get_statistics()
        self.stats.update(doc_stats)

    def get_chat_service(self) -> ChatService:
        """チャットサービスを取得."""
        return self.chat_service

    def get_todo_service(self) -> TodoService:
        """ToDoサービスを取得."""
        return self.todo_service

    def get_document_service(self) -> DocumentService:
        """ドキュメントサービスを取得."""
        return self.document_service

    async def check_lm_studio(self) -> bool:
        """LM Studioへの接続を確認し、モデル情報を取得する.

        Returns:
            bool: 接続できた場合はTrue

        """
        return await self.document_service.check_lm_studio()

    def load_db(self) -> bool:
        """FAISSベクトルストアをロードする.

        Returns:
            bool: ロードできた場合はTrue

        """
        success = self.document_service.load_database()
        if success:
            self._sync_statistics()
        return success

    def get_retriever(self):
        """ドキュメントリトリーバーを取得.

        Returns:
            リトリーバーオブジェクト

        """
        return self.document_service.get_retriever()

    async def rebuild_db(
        self,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> tuple[bool, str]:
        """ベクトルストアを再構築する.

        Args:
            progress_callback: 進行状況を通知するコールバック

        Returns:
            tuple[成功フラグ, メッセージ]

        """
        self.stats["is_rebuilding"] = True
        self._rebuild_cancel_event.clear()

        try:
            # 進行状況コールバックをラップしてstats内のstatus_textを更新
            def _wrapped_progress_callback(status: str) -> None:
                self.stats["status_text"] = status
                if progress_callback:
                    progress_callback(status)

            success, message = await self.document_service.rebuild_database(
                cancel_event=self._rebuild_cancel_event,
                progress_callback=_wrapped_progress_callback,
            )
            if success:
                # 再構築後にベクトルストアをロード
                self.document_service.load_database()
                self._sync_statistics()
            return success, message

        except Exception as e:
            return False, f"Unexpected error during rebuild: {str(e)}"
        finally:
            self.stats["is_rebuilding"] = False
            self.stats["status_text"] = ""

    def cancel_rebuild(self) -> None:
        """再構築を中断する."""
        self._rebuild_cancel_event.set()

    def list_chats(self) -> List[Dict[str, str]]:
        """保存されているチャット履歴の一覧を取得.

        Returns:
            チャットリスト

        """
        return self.chat_service.list_chat_histories()

    def load_chat(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """特定のチャット履歴をロード.

        Args:
            chat_id: チャットID

        Returns:
            チャットデータ

        """
        return self.chat_service.load_chat_history(chat_id)

    def save_chat(self, chat_id: str, messages: List[Dict[str, Any]], title: Optional[str] = None) -> None:
        """チャット履歴を保存.

        Args:
            chat_id: チャットID
            messages: メッセージリスト
            title: タイトル

        """
        self.chat_service.save_chat_history(chat_id, messages, title)

    def delete_chat(self, chat_id: str) -> None:
        """チャット履歴を削除.

        Args:
            chat_id: チャットID

        """
        self.chat_service.delete_chat_history(chat_id)

    def update_user_settings(self, user_storage: Dict[str, Any]) -> None:
        """ユーザーストレージの設定で更新.

        Args:
            user_storage: ユーザーストレージ

        """
        self.config.update_from_user_storage(user_storage)
        self.mode = self.config.app.mode

    def get_user_settings(self) -> Dict[str, Any]:
        """ユーザー設定を取得.

        Returns:
            ユーザー設定

        """
        return self.config.to_user_storage()

    @property
    def vector_store(self):
        """ベクトルストアの実体を取得 (UI互換性用)."""
        return self.document_service.vector_store.vectorstore if self.document_service.vector_store else None