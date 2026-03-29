"""
RAG Backendの基本クラス
CodeSentinelのRAG機能の基底クラスを定義します。
サービスオーケストレーターとして各サービスを管理します。
"""

from typing import Dict, Any, List, Optional

from config import Settings, settings
from rag.service_container import ServiceContainer
from rag.interfaces import IChatService, ITodoService, IDocumentService


class RAGBackend:
    """
    RAG（Retrieval-Augmented Generation）のバックエンド処理を管理するクラス
    サービスオーケストレーターとして各サービスを連携させます
    """
    
    def __init__(self, config: Optional[Settings] = None):
        """
        初期化
        
        Args:
            config: 設定オブジェクト。Noneの場合はデフォルト設定を使用
        """
        self.config = config or settings
        self.mode = self.config.app.mode
        
        # サービスコンテナの初期化
        self.service_container = ServiceContainer(self.config)
        
        # 統計情報（ドキュメントサービスから取得）
        self.stats = {
            "total_chunks": 0,
            "is_rebuilding": False,
            "lm_connected": False,
            "model": "N/A",
            "revision": "v0.3.8",
            "last_rebuild": "Never"
        }
        
        # 初期化
        self._initialize_directories()
        self._initialize_services()
    
    def _initialize_directories(self):
        """必要なディレクトリの初期化"""
        # チャット履歴ディレクトリ
        self.config.paths.chat_dir.mkdir(exist_ok=True)
        
        # ベクトルストアディレクトリ
        self.config.paths.db_full_path.mkdir(exist_ok=True)
    
    def _initialize_services(self):
        """サービスを初期化"""
        self.service_container.initialize()
        
        # 初期化後に統計情報を同期
        self._sync_statistics()
    
    def _sync_statistics(self):
        """統計情報を同期"""
        document_service = self.get_document_service()
        if document_service:
            doc_stats = document_service.get_statistics()
            self.stats.update(doc_stats)
    
    def get_chat_service(self) -> IChatService:
        """チャットサービスを取得"""
        return self.service_container.get_chat_service()
    
    def get_todo_service(self) -> ITodoService:
        """ToDoサービスを取得"""
        return self.service_container.get_todo_service()
    
    def get_document_service(self) -> IDocumentService:
        """ドキュメントサービスを取得"""
        return self.service_container.get_document_service()
    
    async def check_lm_studio(self) -> bool:
        """
        LM Studioへの接続を確認し、モデル情報を取得する
        
        Returns:
            bool: 接続できた場合はTrue
        """
        document_service = self.get_document_service()
        if document_service:
            return await document_service.check_lm_studio()
        return False
    
    def load_db(self) -> bool:
        """
        FAISSベクトルストアをロードする
        
        Returns:
            bool: ロードできた場合はTrue
        """
        document_service = self.get_document_service()
        if document_service:
            success = document_service.load_database()
            if success:
                self._sync_statistics()
            return success
        return False
    
    def get_retriever(self):
        """
        ドキュメントリトリーバーを取得
        
        Returns:
            リトリーバーオブジェクト
        """
        document_service = self.get_document_service()
        if document_service:
            return document_service.get_retriever()
        return None
    
    async def rebuild_db(self) -> tuple[bool, str]:
        """
        ベクトルストアを再構築する
        
        Returns:
            tuple[成功フラグ, メッセージ]
        """
        self.stats["is_rebuilding"] = True
        
        try:
            document_service = self.get_document_service()
            if document_service:
                success, message = await document_service.rebuild_database()
                if success:
                    self._sync_statistics()
                return success, message
            
            return False, "Document service not available"
            
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
        chat_service = self.get_chat_service()
        if chat_service:
            return chat_service.list_chat_histories()
        return []
    
    def load_chat(self, chat_id: str) -> Optional[Dict]:
        """
        特定のチャット履歴をロード
        
        Args:
            chat_id: チャットID
            
        Returns:
            チャットデータ
        """
        chat_service = self.get_chat_service()
        if chat_service:
            return chat_service.load_chat_history(chat_id)
        return None
    
    def save_chat(self, chat_id: str, messages: List[Dict], title: Optional[str] = None):
        """
        チャット履歴を保存
        
        Args:
            chat_id: チャットID
            messages: メッセージリスト
            title: タイトル
        """
        chat_service = self.get_chat_service()
        if chat_service:
            chat_service.save_chat_history(chat_id, messages, title)
    
    def delete_chat(self, chat_id: str):
        """
        チャット履歴を削除
        
        Args:
            chat_id: チャットID
        """
        chat_service = self.get_chat_service()
        if chat_service:
            chat_service.delete_chat_history(chat_id)
    
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