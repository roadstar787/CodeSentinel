"""リポジトリ層のインターフェース定義
データアクセスロジックをカプセル化します。.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from src.config.settings import Settings


class IFileStorage(ABC):
    """ファイルストレージのインターフェース."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """ファイルが存在するか確認."""
        pass

    @abstractmethod
    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """テキストファイルを読み込む."""
        pass

    @abstractmethod
    def write_text(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """テキストファイルを書き込む."""
        pass

    @abstractmethod
    def delete(self, path: str) -> bool:
        """ファイルを削除."""
        pass

    @abstractmethod
    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """ディレクトリ内のファイルをリストアップ."""
        pass

    @abstractmethod
    def mkdir(self, path: str, exist_ok: bool = True) -> None:
        """ディレクトリを作成."""
        pass


class IJsonRepository(ABC):
    """JSONデータリポジトリのインターフェース."""

    @abstractmethod
    def save(self, data: Dict[str, Any], path: str) -> None:
        """JSONデータを保存."""
        pass

    @abstractmethod
    def load(self, path: str) -> Optional[Dict[str, Any]]:
        """JSONデータを読み込む."""
        pass

    @abstractmethod
    def delete(self, path: str) -> bool:
        """JSONファイルを削除."""
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """JSONファイルが存在するか確認."""
        pass


class IVectorStore(ABC):
    """ベクトルストアリポジトリのインターフェース."""

    @abstractmethod
    def as_retriever(self, search_kwargs: Optional[Dict[str, Any]] = None) -> Any:
        """リトリーバーとして取得."""
        pass

    @abstractmethod
    def save_local(self, db_path: str) -> None:
        """ベクトルストアをローカルに保存."""
        pass

    @property
    @abstractmethod
    def index(self) -> Any:
        """ベクトルストアのインデックスを取得."""
        pass

    @classmethod
    @abstractmethod
    def load_local(
        cls,
        db_path: str,
        config: Settings,
        allow_dangerous_deserialization: bool = False
    ) -> "IVectorStore":
        """ローカルからベクトルストアをロード."""
        pass

    @classmethod
    @abstractmethod
    def from_documents(
        cls,
        documents: List,
        config: Settings
    ) -> "IVectorStore":
        """ドキュメントからベクトルストアを作成."""
        pass