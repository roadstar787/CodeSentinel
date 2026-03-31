"""サービス層のインターフェース定義
各サービスクラスが実装すべき契約を定義します。.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IChatService(ABC):
    """チャットサービスのインターフェース."""

    @abstractmethod
    async def generate_response(self, query: str, context: str, mode: str = "Normal") -> dict[str, Any]:
        """チャット応答を生成."""
        pass

    @abstractmethod
    def process_search_results(self, docs: list) -> list[tuple]:
        """検索結果を処理."""
        pass

    @abstractmethod
    def format_context(self, docs: list) -> str:
        """コンテキストをフォーマット."""
        pass

    @abstractmethod
    def save_chat_history(self, chat_id: str, messages: list[dict[str, Any]], title: str | None = None):
        """チャット履歴を保存."""
        pass

    @abstractmethod
    def load_chat_history(self, chat_id: str) -> dict | None:
        """チャット履歴をロード."""
        pass

    @abstractmethod
    def delete_chat_history(self, chat_id: str):
        """チャット履歴を削除."""
        pass

    @abstractmethod
    def list_chat_histories(self) -> list[dict[str, str]]:
        """保存されたチャット履歴の一覧を取得."""
        pass


class ITodoService(ABC):
    """ToDoサービスのインターフェース."""

    @abstractmethod
    def add_todo(self, title: str, description: str = "", priority: str = "medium", due_date: str | None = None) -> dict[str, Any]:
        """ToDoを追加."""
        pass

    @abstractmethod
    def update_todo(self, todo_id: str, title: str | None = None, description: str | None = None,
                    priority: str | None = None, due_date: str | None = None,
                    completed: bool | None = None) -> dict[str, Any] | None:
        """ToDoを更新."""
        pass

    @abstractmethod
    def delete_todo(self, todo_id: str) -> bool:
        """ToDoを削除."""
        pass

    @abstractmethod
    def load_todo(self, todo_id: str) -> dict[str, Any] | None:
        """ToDoをロード."""
        pass

    @abstractmethod
    def list_todos(self, show_completed: bool = True, sort_by: str = "created_at", sort_order: str = "desc") -> list[dict[str, Any]]:
        """ToDoリストを取得."""
        pass

    @abstractmethod
    def toggle_todo_completion(self, todo_id: str) -> dict[str, Any] | None:
        """ToDoの完了状態を切り替え."""
        pass

    @abstractmethod
    def get_todo_statistics(self) -> dict[str, Any]:
        """ToDo統計情報を取得."""
        pass


class IDocumentService(ABC):
    """ドキュメントサービスのインターフェース."""

    @abstractmethod
    async def rebuild_database(self) -> tuple[bool, str]:
        """ベクトルストアを再構築."""
        pass

    @abstractmethod
    def load_database(self) -> bool:
        """FAISSベクトルストアをロード."""
        pass

    @abstractmethod
    def get_retriever(self):
        """ドキュメントリトリーバーを取得."""
        pass

    @abstractmethod
    async def check_lm_studio(self) -> bool:
        """LM Studioへの接続を確認."""
        pass

    @abstractmethod
    def get_statistics(self) -> dict[str, Any]:
        """統計情報を取得."""
        pass

    @abstractmethod
    def update_statistics(self, stats: dict[str, Any]):
        """統計情報を更新."""
        pass
