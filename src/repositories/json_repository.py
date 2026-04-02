"""JSONデータリポジトリの実装
JSONファイルの読み書きを提供します.
"""

import json
from typing import Any, Dict, Optional

from src.interfaces.repositories import IFileStorage, IJsonRepository


class JsonRepository(IJsonRepository):
    """JSONデータリポジトリの実装クラス."""

    def __init__(self, file_storage: IFileStorage):
        """初期化.

        Args:
            file_storage: ファイルストレージインスタンス

        """
        self.file_storage = file_storage

    def save(self, data: Dict[str, Any], path: str) -> None:
        """JSONデータを保存.

        Args:
            data: 保存するデータ
            path: 保存先パス

        """
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        self.file_storage.write_text(path, json_str)

    def load(self, path: str) -> Optional[Dict[str, Any]]:
        """JSONデータを読み込む.

        Args:
            path: ファイルパス

        Returns:
            読み込んだデータ。ファイルが存在しない場合はNone

        """
        if not self.file_storage.exists(path):
            return None

        try:
            json_str = self.file_storage.read_text(path)
            return json.loads(json_str)
        except (json.JSONDecodeError, Exception):
            return None

    def delete(self, path: str) -> bool:
        """JSONファイルを削除.

        Args:
            path: ファイルパス

        Returns:
            bool: 削除に成功した場合はTrue

        """
        return self.file_storage.delete(path)

    def exists(self, path: str) -> bool:
        """JSONファイルが存在するか確認.

        Args:
            path: ファイルパス

        Returns:
            bool: ファイルが存在する場合はTrue

        """
        return self.file_storage.exists(path)