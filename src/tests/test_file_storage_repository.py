"""FileStorageRepositoryのテスト"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path

from src.repositories.file_storage_repository import FileStorageRepository


class TestFileStorageRepository:
    """FileStorageRepositoryクラスのテスト"""

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリの作成"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def repository(self, temp_dir):
        """FileStorageRepositoryのインスタンス作成"""
        return FileStorageRepository()

    def test_exists_true(self, repository, temp_dir):
        """ファイルが存在する場合のテスト"""
        file_path = temp_dir / "test.txt"
        file_path.write_text("test content")
        
        assert repository.exists(str(file_path)) is True

    def test_exists_false(self, repository, temp_dir):
        """ファイルが存在しない場合のテスト"""
        file_path = temp_dir / "nonexistent.txt"
        
        assert repository.exists(str(file_path)) is False

    def test_read_text(self, repository, temp_dir):
        """テキストファイルの読み込みテスト"""
        file_path = temp_dir / "test.txt"
        expected_content = "テストコンテンツ"
        file_path.write_text(expected_content, encoding="utf-8")
        
        result = repository.read_text(str(file_path))
        assert result == expected_content

    def test_read_text_with_encoding(self, repository, temp_dir):
        """エンコーディング指定付きのテキストファイル読み込みテスト"""
        file_path = temp_dir / "test_cp932.txt"
        expected_content = "日本語テスト"
        file_path.write_text(expected_content, encoding="cp932")
        
        result = repository.read_text(str(file_path), encoding="cp932")
        assert result == expected_content

    def test_write_text(self, repository, temp_dir):
        """テキストファイルの書き込みテスト"""
        file_path = temp_dir / "output.txt"
        content = "書き込みテスト"
        
        repository.write_text(str(file_path), content)
        
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == content

    def test_write_text_creates_parent_dirs(self, repository, temp_dir):
        """書き込み時に親ディレクトリを自動作成するテスト"""
        file_path = temp_dir / "sub" / "dir" / "output.txt"
        content = "ネストされた書き込み"
        
        repository.write_text(str(file_path), content)
        
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == content

    def test_delete_existing_file(self, repository, temp_dir):
        """既存ファイルの削除テスト"""
        file_path = temp_dir / "delete_me.txt"
        file_path.write_text("消して")
        
        result = repository.delete(str(file_path))
        
        assert result is True
        assert not file_path.exists()

    def test_delete_nonexistent_file(self, repository, temp_dir):
        """存在しないファイルの削除テスト"""
        file_path = temp_dir / "not_exist.txt"
        
        result = repository.delete(str(file_path))
        
        assert result is False

    def test_list_files(self, repository, temp_dir):
        """ファイル一覧の取得テスト"""
        # テストファイルの作成
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.txt").write_text("content2")
        (temp_dir / "file3.json").write_text("{}")
        
        result = repository.list_files(str(temp_dir), "*.txt")
        
        assert len(result) == 2
        assert all(r.endswith(".txt") for r in result)

    def test_list_files_all(self, repository, temp_dir):
        """全ファイル一覧の取得テスト"""
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.json").write_text("{}")
        
        result = repository.list_files(str(temp_dir))
        
        assert len(result) == 2

    def test_list_files_nonexistent_directory(self, repository, temp_dir):
        """存在しないディレクトリのファイル一覧取得テスト"""
        result = repository.list_files(str(temp_dir / "nonexistent"))
        
        assert result == []

    def test_mkdir(self, repository, temp_dir):
        """ディレクトリ作成テスト"""
        new_dir = temp_dir / "new_dir"
        
        repository.mkdir(str(new_dir))
        
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_mkdir_nested(self, repository, temp_dir):
        """ネストされたディレクトリ作成テスト"""
        new_dir = temp_dir / "level1" / "level2" / "level3"
        
        repository.mkdir(str(new_dir))
        
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_mkdir_exist_ok(self, repository, temp_dir):
        """既存ディレクトリに対するmkdir(存在許可)テスト"""
        new_dir = temp_dir / "existing_dir"
        new_dir.mkdir()
        
        # 例外が投げられないことを確認
        repository.mkdir(str(new_dir), exist_ok=True)

    def test_write_and_read_roundtrip(self, repository, temp_dir):
        """書き込み→読み込みのラウンドトリップテスト"""
        file_path = temp_dir / "roundtrip.txt"
        original_content = "ラウンドトリップ テスト\n改行含む"
        
        repository.write_text(str(file_path), original_content)
        result = repository.read_text(str(file_path))
        
        assert result == original_content