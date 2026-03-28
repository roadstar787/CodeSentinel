"""
RAG Backendの基本クラス
CodeSentinelのRAG機能の基底クラスを定義します。
"""

import os
import asyncio
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import Counter

import httpx
import psutil

from ..config import Settings, settings
from .vector_store import VectorStoreManager
from .document_processor import DocumentProcessor
from .chat_service import ChatService


class RAGBackend:
    """
    RAG（Retrieval-Augmented Generation）のバックエンド処理を管理するクラス
    """
    
    def __init__(self, config: Optional[Settings] = None):
        """
        初期化
        
        Args:
            config: 設定オブジェクト。Noneの場合はデフォルト設定を使用
        """
        self.config = config or settings
        self.mode = self.config.app.mode
        
        # 統計情報
        self.stats = {
            "total_chunks": 0,
            "is_rebuilding": False,
            "lm_connected": False,
            "model": "N/A",
            "revision": "v0.3.8",
            "last_rebuild": "Never"
        }
        
        # サブコンポーネント
        self.vector_store = None
        self.document_processor = DocumentProcessor(self.config)
        self.chat_service = ChatService(self.config)
        
        # 初期化
        self._initialize_directories()
        self.load_db()
    
    def _initialize_directories(self):
        """必要なディレクトリの初期化"""
        # チャット履歴ディレクトリ
        self.config.paths.chat_dir.mkdir(exist_ok=True)
        
        # ベクトルストアディレクトリ
        self.config.paths.db_full_path.mkdir(exist_ok=True)
    
    async def check_lm_studio(self) -> bool:
        """
        LM Studioへの接続を確認し、モデル情報を取得する
        
        Returns:
            bool: 接続できた場合はTrue
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self.config.lm_studio.get_models_url(), 
                    timeout=self.config.lm_studio.timeout
                )
                if resp.status_code == 200:
                    self.stats["lm_connected"] = True
                    data = resp.json()
                    if data.get('data'):
                        self.stats["model"] = data['data'][0]['id']
                    return True
                else:
                    print(f"LM Studio returned status: {resp.status_code}")
        except Exception as e:
            print(f"Connection Error Detail: {e}")
        
        self.stats["lm_connected"] = False
        return False
    
    def load_db(self) -> bool:
        """
        FAISSベクトルストアをロードする
        
        Returns:
            bool: ロードできた場合はTrue
        """
        if os.path.exists(self.config.paths.db_path):
            try:
                self.vector_store = VectorStoreManager.load_local(
                    self.config.paths.db_path, 
                    self.config.lm_studio,
                    allow_dangerous_deserialization=True
                )
                self.stats["total_chunks"] = self.vector_store.index.ntotal
                return True
            except Exception:
                return False
        return False
    
    def get_retriever(self):
        """
        ドキュメントリトリーバーを取得
        
        Returns:
            リトリーバーオブジェクト
        """
        if self.vector_store:
            return self.vector_store.as_retriever(search_kwargs={"k": self.config.rag.search_k})
        return None
    
    async def rebuild_db(self) -> tuple[bool, str]:
        """
        ベクトルストアを再構築する
        
        Returns:
            tuple[成功フラグ, メッセージ]
        """
        self.stats["is_rebuilding"] = True
        
        try:
            # LM Studioへの接続確認
            connected = await self.check_lm_studio()
            if not connected:
                return False, "LM Studio connection failed"
            
            # ドキュメント処理とベクトルストア構築
            success, message = await self.document_processor.process_all_documents()
            if not success:
                return False, message
            
            # ベクトルストアの保存
            self.vector_store.save_local(self.config.paths.db_path)
            self.stats["total_chunks"] = len(self.document_processor.processed_documents)
            self.stats["last_rebuild"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            return True, "SUCCESS"
            
        except Exception as e:
            return False, f"Unexpected error during rebuild: {str(e)}"
        finally:
            self.stats["is_rebuilding"] = False
    
    def list_chats(self) -> List[Dict[str, str]]:
        """
        保存されているチャット履歴の一覧を取得
        
        Returns:
            チャットリスト
        """
        chats = []
        for f in self.config.paths.chat_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as j:
                    data = json.load(j)
                    chats.append({
                        "id": f.stem,
                        "title": data.get("title", "Untitled Chat"),
                        "date": data.get("date", "")
                    })
            except Exception:
                continue
        return sorted(chats, key=lambda x: x["date"], reverse=True)
    
    def load_chat(self, chat_id: str) -> Optional[Dict]:
        """
        特定のチャット履歴をロード
        
        Args:
            chat_id: チャットID
            
        Returns:
            チャットデータ
        """
        path = self.config.paths.chat_dir / f"{chat_id}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    def save_chat(self, chat_id: str, messages: List[Dict], title: Optional[str] = None):
        """
        チャット履歴を保存
        
        Args:
            chat_id: チャットID
            messages: メッセージリスト
            title: タイトル
        """
        path = self.config.paths.chat_dir / f"{chat_id}.json"
        
        # 既存データの読み込み
        existing_title = "New Chat"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    existing_title = old_data.get("title", existing_title)
            except Exception:
                pass
        
        data = {
            "title": title if title else existing_title,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": messages
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def delete_chat(self, chat_id: str):
        """
        チャット履歴を削除
        
        Args:
            chat_id: チャットID
        """
        path = self.config.paths.chat_dir / f"{chat_id}.json"
        if path.exists():
            path.unlink()
    
    def update_user_settings(self, user_storage: Dict[str, Any]):
        """
        ユーザーストレージの設定で更新
        
        Args:
            user_storage: ユーザーストレージ
        """
        self.config.update_from_user_storage(user_storage)
        self.mode = self.config.app.mode
    
    def get_user_settings(self) -> Dict[str, Any]:
        """
        ユーザー設定を取得
        
        Returns:
            ユーザー設定
        """
        return self.config.to_user_storage()