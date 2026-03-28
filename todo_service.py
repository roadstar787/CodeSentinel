"""
ToDoリストサービスモジュール
ToDoリスト関連のビジネスロジックを管理します。
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class TodoService:
    """ToDoリストサービスを提供するクラス"""
    
    def __init__(self, todo_dir_path: Path):
        """
        初期化
        
        Args:
            todo_dir_path: ToDoリスト保存ディレクトリ
        """
        self.todo_dir = todo_dir_path
        self.todo_dir.mkdir(exist_ok=True)
    
    def generate_todo_id(self) -> str:
        """
        ToDo IDを生成
        
        Returns:
            ToDo ID
        """
        return str(uuid.uuid4())
    
    def add_todo(
        self, 
        title: str, 
        description: str = "", 
        priority: str = "medium",
        due_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ToDoを追加
        
        Args:
            title: タイトル
            description: 説明
            priority: 優先度 (high, medium, low)
            due_date: 期限 (YYYY-MM-DD形式)
            
        Returns:
            追加したToDoデータ
        """
        todo_id = self.generate_todo_id()
        todo_data = {
            "id": todo_id,
            "title": title,
            "description": description,
            "priority": priority,
            "due_date": due_date,
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # ファイルに保存
        self._save_todo(todo_id, todo_data)
        
        return todo_data
    
    def update_todo(
        self, 
        todo_id: str, 
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[str] = None,
        completed: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """
        ToDoを更新
        
        Args:
            todo_id: ToDo ID
            title: タイトル
            description: 説明
            priority: 優先度
            due_date: 期限
            completed: 完了状態
            
        Returns:
            更新したToDoデータ
        """
        todo_data = self.load_todo(todo_id)
        if not todo_data:
            return None
        
        # 値を更新
        if title is not None:
            todo_data["title"] = title
        if description is not None:
            todo_data["description"] = description
        if priority is not None:
            todo_data["priority"] = priority
        if due_date is not None:
            todo_data["due_date"] = due_date
        if completed is not None:
            todo_data["completed"] = completed
        
        todo_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # ファイルに保存
        self._save_todo(todo_id, todo_data)
        
        return todo_data
    
    def delete_todo(self, todo_id: str) -> bool:
        """
        ToDoを削除
        
        Args:
            todo_id: ToDo ID
            
        Returns:
            削除できたかどうか
        """
        path = self.todo_dir / f"{todo_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
    
    def load_todo(self, todo_id: str) -> Optional[Dict[str, Any]]:
        """
        ToDoをロード
        
        Args:
            todo_id: ToDo ID
            
        Returns:
            ToDoデータ
        """
        path = self.todo_dir / f"{todo_id}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    def list_todos(
        self, 
        show_completed: bool = True,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        ToDoリストを取得
        
        Args:
            show_completed: 完了したToDoを含めるかどうか
            sort_by: ソート基準 (created_at, updated_at, priority, due_date)
            sort_order: ソート順 (asc, desc)
            
        Returns:
            ToDoリスト
        """
        todos = []
        for f in self.todo_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as j:
                    data = json.load(j)
                    if show_completed or not data.get("completed", False):
                        todos.append(data)
            except Exception:
                continue
        
        # ソート
        reverse = sort_order == "desc"
        if sort_by in ["created_at", "updated_at"]:
            todos.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)
        elif sort_by == "priority":
            priority_order = {"high": 0, "medium": 1, "low": 2}
            todos.sort(key=lambda x: priority_order.get(x.get(sort_by, "medium"), 3), reverse=not reverse)
        elif sort_by == "due_date":
            todos.sort(key=lambda x: x.get(sort_by, "") or "9999-12-31", reverse=reverse)
        
        return todos
    
    def toggle_todo_completion(self, todo_id: str) -> Optional[Dict[str, Any]]:
        """
        ToDoの完了状態を切り替え
        
        Args:
            todo_id: ToDo ID
            
        Returns:
            更新したToDoデータ
        """
        todo_data = self.load_todo(todo_id)
        if not todo_data:
            return None
        
        todo_data["completed"] = not todo_data.get("completed", False)
        todo_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # ファイルに保存
        self._save_todo(todo_id, todo_data)
        
        return todo_data
    
    def _save_todo(self, todo_id: str, todo_data: Dict[str, Any]):
        """
        ToDoをファイルに保存
        
        Args:
            todo_id: ToDo ID
            todo_data: ToDoデータ
        """
        path = self.todo_dir / f"{todo_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(todo_data, f, ensure_ascii=False, indent=2)
    
    def get_todo_statistics(self) -> Dict[str, Any]:
        """
        ToDo統計情報を取得
        
        Returns:
            統計情報
        """
        todos = self.list_todos(show_completed=True)
        total = len(todos)
        completed = sum(1 for todo in todos if todo.get("completed", False))
        pending = total - completed
        
        priority_counts = {"high": 0, "medium": 0, "low": 0}
        for todo in todos:
            priority = todo.get("priority", "medium")
            if priority in priority_counts:
                priority_counts[priority] += 1
        
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "priority_distribution": priority_counts
        }