"""リポジトリ層のインターフェース定義
データアクセスロジックをカプセル化します。.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


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