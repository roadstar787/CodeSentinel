"""
ドキュメントサービスモジュール
ドキュメント関連のビジネスロジックを管理します。
"""

import os
import asyncio
from typing import Dict, Any, List, Optional

import httpx

from langchain_core.documents import Document
from rag.repositories import VectorStoreRepository, EmbeddingService, FileStorageRepository
from rag.document_processor import DocumentProcessor
from config.config import Settings
from rag.interfaces import IDocumentService


class DocumentService(IDocumentService):
    """ドキュメントサービスを提供するクラス"""
    
    def __init__(self, config: Settings):
        """
        初期化
        
        Args:
            config: 設定オブジェクト
        """
        self.config = config
        
        # リポジトリの初期化
        self.file_storage = FileStorageRepository()
        self.vector_store = VectorStoreRepository(config)
        self.embedding_service = EmbeddingService(config)
        
        # ドキュメントプロセッサ
        self.document_processor = DocumentProcessor(config)
        
        # 統計情報
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
        self.load_database()
    
    def _initialize_directories(self):
        """必要なディレクトリの初期化"""
        # ベクトルストアディレクトリ
        self.file_storage.mkdir(str(self.config.paths.db_full_path))
    
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
    
    def load_database(self) -> bool:
        """
        FAISSベクトルストアをロードする
        
        Returns:
            bool: ロードできた場合はTrue
        """
        if self.file_storage.exists(self.config.paths.db_path):
            try:
                self.vector_store = VectorStoreRepository.load_local(
                    self.config.paths.db_path, 
                    self.config,
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
    
    async def rebuild_database(self) -> tuple[bool, str]:
        """
        ベクトルストアを再構築する
        
        Returns:
            tuple[成功フラグ, メッセージ]
        """
        self.stats["is_rebuilding"] = True
        print(f"[DEBUG] REBUILD DB TASK STARTED")
        
        try:
            # LM Studioへの接続確認
            connected = await self.check_lm_studio()
            if not connected:
                print(f"[DEBUG] REBUILD FAIL: LM Studio not connected.")
                return False, "LM Studio connection failed"
            
            # ドキュメント処理とベクトルストア構築
            success, message = await self.document_processor.process_all_documents()
            if not success:
                print(f"[DEBUG] REBUILD FAIL: Parsing failed. {message}")
                return False, message
            
            # ベクトルストアの構築（新規作成） - 長時間かかるため別スレッドで実行
            processed_docs = self.document_processor.get_processed_documents()
            # LangChainのDocumentオブジェクトに再変換
            langchain_docs = [
                Document(page_content=d.content, metadata=d.metadata) 
                for d in processed_docs
            ]
            
            print(f"[DEBUG] EMBEDDING PHASE STARTED - Total {len(langchain_docs)} chunks.")
            # ドキュメントからベクトルストアを新規作成（LM Studio通信とブロッキングを回避）
            self.vector_store = await asyncio.to_thread(
                VectorStoreRepository.from_documents, 
                langchain_docs, 
                self.config
            )
            print(f"[DEBUG] EMBEDDING PHASE FINISHED - Vector store created.")
            
            # ベクトルストアの保存（別スレッドで実行）
            print(f"[DEBUG] SAVING DB TO DISK...")
            await asyncio.to_thread(
                self.vector_store.save_local, 
                self.config.paths.db_path
            )
            print(f"[DEBUG] DB SAVED. Rebuild Complete.")
            
            # 統計情報を更新
            self.stats["total_chunks"] = len(langchain_docs)
            self.stats["last_rebuild"] = self._get_current_timestamp()
            
            return True, "SUCCESS"
            
        except Exception as e:
            print(f"[DEBUG] REBUILD CRASH: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Unexpected error during rebuild: {str(e)}"
        finally:
            self.stats["is_rebuilding"] = False
            print(f"[DEBUG] REBUILD DB TASK FINISHED")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        統計情報を取得
        
        Returns:
            統計情報
        """
        return self.stats
    
    def update_statistics(self, stats: Dict[str, Any]):
        """
        統計情報を更新
        
        Args:
            stats: 更新する統計情報
        """
        self.stats.update(stats)
    
    def _get_current_timestamp(self) -> str:
        """現在のタイムスタンプを取得"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")