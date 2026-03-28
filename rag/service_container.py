"""
サービスコンテナモジュール
依存性注入とサービス管理を行います。
"""

from typing import Dict, Any, Optional
from ..config import Settings
from .interfaces import IChatService, ITodoService, IDocumentService, ISettingsService
from .chat_service import ChatService
from .document_service import DocumentService
from todo_service import TodoService


class ServiceContainer:
    """サービスコンテナクラス"""
    
    def __init__(self, config: Settings):
        """
        初期化
        
        Args:
            config: 設定オブジェクト
        """
        self._config = config
        self._services: Dict[str, Any] = {}
        self._initialized = False
    
    def initialize(self):
        """サービスコンテナを初期化"""
        if self._initialized:
            return
        
        # 各サービスの初期化
        self._services['chat'] = ChatService(self._config)
        self._services['document'] = DocumentService(self._config)
        self._services['todo'] = TodoService(self._config.paths.todo_dir_path)
        
        self._initialized = True
    
    def get_chat_service(self) -> IChatService:
        """チャットサービスを取得"""
        if not self._initialized:
            self.initialize()
        return self._services['chat']
    
    def get_document_service(self) -> IDocumentService:
        """ドキュメントサービスを取得"""
        if not self._initialized:
            self.initialize()
        return self._services['document']
    
    def get_todo_service(self) -> ITodoService:
        """ToDoサービスを取得"""
        if not self._initialized:
            self.initialize()
        return self._services['todo']
    
    def get_settings_service(self) -> ISettingsService:
        """設定サービスを取得"""
        if not self._initialized:
            self.initialize()
        # 現在はRAGBackendが設定サービスの役割を担う
        return self._services.get('settings', None)
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """指定されたサービスを取得
        
        Args:
            service_name: サービス名 ('chat', 'document', 'todo')
            
        Returns:
            サービスインスタンス
        """
        if not self._initialized:
            self.initialize()
        
        return self._services.get(service_name)
    
    def register_service(self, service_name: str, service_instance: Any):
        """サービスを登録
        
        Args:
            service_name: サービス名
            service_instance: サービスインスタンス
        """
        self._services[service_name] = service_instance
        if not self._initialized:
            self._initialized = True
    
    def is_initialized(self) -> bool:
        """初期化状態を確認"""
        return self._initialized