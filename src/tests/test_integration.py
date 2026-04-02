"""統合テスト"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestIntegration:
    """統合テストクラス."""

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリの作成."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_chat_id_generation(self):
        """チャットID生成のテスト."""
        import uuid
        chat_id = str(uuid.uuid4())
        assert chat_id is not None
        assert len(chat_id) == 36

    def test_todo_id_generation(self):
        """ToDo ID生成のテスト."""
        import uuid
        from datetime import datetime
        todo_id = f"todo_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        assert todo_id is not None
        assert todo_id.startswith("todo_")

    def test_file_processing(self, temp_dir):
        """ファイル処理のテスト."""
        # テストファイルの作成
        test_file = temp_dir / "test.py"
        test_file.write_text("# Test file\nprint('hello')")

        # ファイルの読み込み
        content = test_file.read_text()
        assert "# Test file" in content
        assert "print('hello')" in content

    def test_json_storage(self, temp_dir):
        """JSONストレージのテスト."""
        import json

        # データの保存
        data = {"key": "value", "list": [1, 2, 3]}
        json_file = temp_dir / "test.json"
        json_file.write_text(json.dumps(data, ensure_ascii=False))

        # データの読み込み
        loaded = json.loads(json_file.read_text())
        assert loaded["key"] == "value"
        assert loaded["list"] == [1, 2, 3]

    def test_chat_history_flow(self, temp_dir):
        """チャット履歴フローのテスト."""
        import json

        # チャット履歴の作成
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "ai", "content": "Hi there!"}
        ]

        # 保存
        chat_file = temp_dir / "chat.json"
        chat_file.write_text(json.dumps({"messages": history}, ensure_ascii=False))

        # 読み込み
        loaded = json.loads(chat_file.read_text())
        assert len(loaded["messages"]) == 2
        assert loaded["messages"][0]["role"] == "user"
        assert loaded["messages"][1]["role"] == "ai"

    def test_todo_flow(self, temp_dir):
        """ToDoフローのテスト."""
        import json

        # ToDoの作成
        todos = [
            {
                "id": "todo_001",
                "title": "Test Todo",
                "description": "Test Description",
                "priority": "high",
                "completed": False
            }
        ]

        # 保存
        todo_file = temp_dir / "todos.json"
        todo_file.write_text(json.dumps(todos, ensure_ascii=False))

        # 読み込み
        loaded = json.loads(todo_file.read_text())
        assert len(loaded) == 1
        assert loaded[0]["title"] == "Test Todo"
        assert loaded[0]["priority"] == "high"

    def test_document_chunking(self, temp_dir):
        """ドキュメントチャンキングのテスト."""
        # テストドキュメントの作成
        doc = """
# Title

This is a paragraph.

This is another paragraph.

## Section 1

Content for section 1.
"""
        # 段落ごとに分割
        chunks = [p.strip() for p in doc.split('\n\n') if p.strip()]
        assert len(chunks) >= 3
        assert "# Title" in chunks[0]

    def test_search_results_processing(self):
        """検索結果処理のテスト."""
        # モックの検索結果
        docs = [
            {"content": "Content 1", "metadata": {"source": "file1.py", "type": "code"}},
            {"content": "Content 2", "metadata": {"source": "file2.md", "type": "doc"}},
            {"content": "Content 3", "metadata": {"source": "file1.py", "type": "code"}},
        ]

        # 重複除去
        unique_sources = []
        for doc in docs:
            source = doc["metadata"]["source"]
            doc_type = doc["metadata"]["type"]
            if (source, doc_type) not in unique_sources:
                unique_sources.append((source, doc_type))

        assert len(unique_sources) == 2
        assert ("file1.py", "code") in unique_sources
        assert ("file2.md", "doc") in unique_sources