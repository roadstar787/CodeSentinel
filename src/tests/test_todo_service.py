"""ToDoサービスのテスト."""

from pathlib import Path

import pytest

from config.settings import Settings
from services.todo_service import TodoService


class TestTodoService:
    """ToDoサービスのテストクラス."""

    @pytest.fixture
    def todo_service(self):
        """ToDoサービスのフィクスチャ."""
        config = Settings()
        return TodoService(config.paths.todo_dir_path)

    def test_add_todo(self, todo_service) -> None:
        """ToDo追加のテスト."""
        title = "テストToDo"
        description = "テスト説明"
        priority = "high"
        due_date = "2024-12-31"

        result = todo_service.add_todo(title, description, priority, due_date)

        assert "id" in result
        assert result["title"] == title
        assert result["description"] == description
        assert result["priority"] == priority
        assert result["due_date"] == due_date
        assert result["completed"] is False

    def test_add_todo_minimal(self, todo_service) -> None:
        """ToDo追加の最小テスト."""
        title = "最小テストToDo"

        result = todo_service.add_todo(title)

        assert "id" in result
        assert result["title"] == title
        assert result["priority"] == "medium"
        assert result["completed"] is False

    def test_delete_todo(self, todo_service) -> None:
        """ToDo削除のテスト."""
        # まずToDoを追加
        todo = todo_service.add_todo("削除テスト")

        # 削除を実行
        result = todo_service.delete_todo(todo["id"])

        assert result is True

    def test_list_todos(self, todo_service) -> None:
        """ToDoリスト取得のテスト."""
        # テスト用のToDoを追加
        todo_service.add_todo("リストテスト1")
        todo_service.add_todo("リストテスト2")

        result = todo_service.list_todos()

        assert isinstance(result, list)
        assert len(result) >= 2

    def test_get_todo_statistics(self, todo_service) -> None:
        """ToDo統計情報取得のテスト."""
        # テスト用のToDoを追加
        todo_service.add_todo("統計テスト1")
        todo_service.add_todo("統計テスト2", priority="high")

        result = todo_service.get_todo_statistics()

        assert "total" in result
        assert "completed" in result
        assert "pending" in result
        assert "priority_distribution" in result
        assert isinstance(result["total"], int)
        assert isinstance(result["completed"], int)
        assert isinstance(result["pending"], int)
        assert "high" in result["priority_distribution"]
        assert "medium" in result["priority_distribution"]
        assert "low" in result["priority_distribution"]
