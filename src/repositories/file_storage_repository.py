"""ファイルストレージリポジトリの実装
ファイルI/O操作を提供します.
"""

import os
from pathlib import Path
from typing import List

from src.interfaces.repositories import IFileStorage


class FileStorageRepository(IFileStorage):
    """ファイルストレージリポジトリの実装クラス."""

    def exists(self, path: str) -> bool:
        """ファイルが存在するか確認.

        Args:
            path: ファイルパス

        Returns:
            bool: ファイルが存在する場合はTrue

        """
        return os.path.exists(path)

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """テキストファイルを読み込む.

        Args:
            path: ファイルパス
            encoding: ファイルエンコーディング

        Returns:
            ファイルの内容

        """
        with open(path, "r", encoding=encoding) as f:
            return f.read()

    def write_text(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """テキストファイルを書き込む.

        Args:
            path: ファイルパス
            content: 書き込む内容
            encoding: ファイルエンコーディング

        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding=encoding) as f:
            f.write(content)

    def delete(self, path: str) -> bool:
        """ファイルを削除.

        Args:
            path: ファイルパス

        Returns:
            bool: 削除に成功した場合はTrue

        """
        try:
            if os.path.exists(path):
                os.remove(path)
                return True
            return False
        except Exception:
            return False

    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """ディレクトリ内のファイルをリストアップ.

        Args:
            directory: ディレクトリパス
            pattern: ファイル名パターン（例: "*.txt"）

        Returns:
            ファイルパスのリスト

        """
        try:
            path = Path(directory)
            if path.is_dir():
                return [str(p) for p in path.glob(pattern) if p.is_file()]
            return []
        except Exception:
            return []

    def mkdir(self, path: str, exist_ok: bool = True) -> None:
        """ディレクトリを作成.

        Args:
            path: ディレクトリパス
            exist_ok: 既に存在する場合に許可するかどうか

        """
        Path(path).mkdir(parents=True, exist_ok=exist_ok)