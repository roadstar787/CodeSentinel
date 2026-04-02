"""JsonRepositoryのテスト"""

import pytest
import tempfile
import shutil
from pathlib import Path

from src.repositories.file_storage_repository import FileStorageRepository
from src.repositories.json_repository import JsonRepository


class TestJsonRepository:
    """JsonRepositoryクラスのテスト"""

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリの作成"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def file_storage(self, temp_dir):
        """FileStorageRepositoryのインスタンス作成"""
        return FileStorageRepository()

    @pytest.fixture
    def repository(self, file_storage):
        """JsonRepositoryのインスタンス作成"""
        return JsonRepository(file_storage)

    def test_save_and_load(self, repository, temp_dir):
        """JSONファイルの保存と読み込みテスト"""
        file_path = temp_dir / "test.json"
        data = {"name": "テスト", "value": 123, "nested": {"key": "value"}}
        
        repository.save(data, str(file_path))
        result = repository.load(str(file_path))
        
        assert result == data

    def test_save_creates_parent_dirs(self, repository, temp_dir):
        """保存時に親ディレクトリを自動作成するテスト"""
        file_path = temp_dir / "sub" / "dir" / "nested.json"
        data = {"nested": True}
        
        repository.save(data, str(file_path))
        
        assert file_path.exists()
        result = repository.load(str(file_path))
        assert result == data

    def test_load_nonexistent_file(self, repository, temp_dir):
        """存在しないファイルの読み込みテスト"""
        file_path = temp_dir / "not_exist.json"
        
        result = repository.load(str(file_path))
        
        assert result is None

    def test_delete_existing_file(self, repository, temp_dir):
        """既存JSONファイルの削除テスト"""
        file_path = temp_dir / "delete_me.json"
        data = {"delete": True}
        repository.save(data, str(file_path))
        
        result = repository.delete(str(file_path))
        
        assert result is True
        assert not file_path.exists()

    def test_delete_nonexistent_file(self, repository, temp_dir):
        """存在しないJSONファイルの削除テスト"""
        file_path = temp_dir / "not_exist.json"
        
        result = repository.delete(str(file_path))
        
        assert result is False

    def test_exists_true(self, repository, temp_dir):
        """JSONファイルが存在する場合のテスト"""
        file_path = temp_dir / "exists.json"
        data = {"exists": True}
        repository.save(data, str(file_path))
        
        assert repository.exists(str(file_path)) is True

    def test_exists_false(self, repository, temp_dir):
        """JSONファイルが存在しない場合のテスト"""
        file_path = temp_dir / "not_exist.json"
        
        assert repository.exists(str(file_path)) is False

    def test_save_with_japanese_content(self, repository, temp_dir):
        """日本語コンテンツの保存テスト"""
        file_path = temp_dir / "japanese.json"
        data = {
            "title": "日本語タイトル",
            "description": "これは日本語の説明です",
            "items": ["アイテム1", "アイテム2", "アイテム3"]
        }
        
        repository.save(data, str(file_path))
        result = repository.load(str(file_path))
        
        assert result == data

    def test_save_and_overwrite(self, repository, temp_dir):
        """JSONファイルの上書きテスト"""
        file_path = temp_dir / "overwrite.json"
        
        # 最初の保存
        data_v1 = {"version": 1, "data": "old"}
        repository.save(data_v1, str(file_path))
        
        # 上書き保存
        data_v2 = {"version": 2, "data": "new"}
        repository.save(data_v2, str(file_path))
        
        result = repository.load(str(file_path))
        assert result == data_v2

    def test_load_invalid_json(self, repository, file_storage, temp_dir):
        """無効なJSONファイルの読み込みテスト"""
        file_path = temp_dir / "invalid.json"
        file_storage.write_text(str(file_path), "not valid json")
        
        result = repository.load(str(file_path))
        
        assert result is None

    def test_complex_nested_data(self, repository, temp_dir):
        """複雑なネストされたデータの保存・読み込みテスト"""
        file_path = temp_dir / "complex.json"
        data = {
            "user": {
                "id": 1,
                "name": "テスト太郎",
                "profile": {
                    "age": 30,
                    "languages": ["Python", "日本語", "English"]
                }
            },
            "settings": {
                "theme": "dark",
                "notifications": {
                    "email": True,
                    "push": False,
                    "sms": True
                }
            },
            "items": [
                {"id": 1, "name": "アイテム1", "active": True},
                {"id": 2, "name": "アイテム2", "active": False},
            ]
        }
        
        repository.save(data, str(file_path))
        result = repository.load(str(file_path))
        
        assert result == data
        assert result["user"]["name"] == "テスト太郎"
        assert len(result["items"]) == 2