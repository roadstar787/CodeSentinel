"""ドキュメントサービスモジュール
ドキュメント関連のビジネスロジックを管理します.
"""

import asyncio
from typing import Any, Callable, Dict, Optional

import httpx

from src.config.settings import Settings
from src.repositories.vector_store_repository import VectorStoreRepository
from src.services.document_processor import DocumentProcessor


class DocumentService:
    """ドキュメントサービスを提供するクラス."""

    def __init__(self, config: Settings):
        """初期化.

        Args:
            config: 設定オブジェクト

        """
        self.config = config
        self.vector_store: Optional[VectorStoreRepository] = None
        self.stats: Dict[str, Any] = {
            "total_chunks": 0,
            "last_rebuild": "Never",
            "lm_connected": False,
            "model": "N/A",
            "vector_store_loaded": False
        }

    async def rebuild_database(
        self,
        cancel_event: Optional[asyncio.Event] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> tuple[bool, str]:
        """ベクトルストアを再構築.

        Args:
            cancel_event: キャンセルイベント
            progress_callback: 進行状況を通知するコールバック

        Returns:
            tuple[成功フラグ, メッセージ]

        """
        processor = DocumentProcessor(self.config)
        success, message = await processor.process_all_documents(
            cancel_event=cancel_event,
            progress_callback=progress_callback,
        )

        if not success:
            return False, message

        processed_docs = processor.get_processed_documents()
        if not processed_docs:
            return False, "No documents to index"

        # ProcessedDocumentからLangChain Documentに変換
        from langchain_core.documents import Document
        documents = [
            Document(page_content=doc.content, metadata=doc.metadata)
            for doc in processed_docs
        ]

        self.vector_store = VectorStoreRepository.from_documents(documents, self.config)
        
        # ベクトルストアをローカルに保存
        db_path = str(self.config.paths.db_full_path)
        self.vector_store.save_local(db_path)
        
        self.stats["total_chunks"] = len(documents)
        self.stats["last_rebuild"] = "Just now"
        self.stats["vector_store_loaded"] = True

        return True, f"Indexed {len(documents)} chunks"

    def load_database(self) -> bool:
        """FAISSベクトルストアをロード.

        Returns:
            bool: ロードできた場合はTrue

        """
        db_path = str(self.config.paths.db_full_path)
        try:
            print(f"[DEBUG] Loading database from {db_path}")
            self.vector_store = VectorStoreRepository.load_local(
                db_path, self.config, allow_dangerous_deserialization=True
            )
            print(f"[DEBUG] Database loaded successfully")
            self.stats["vector_store_loaded"] = True
            # チャンク数を更新
            if self.vector_store and self.vector_store.index:
                self.stats["total_chunks"] = self.vector_store.index.ntotal
                print(f"[DEBUG] Total chunks: {self.stats['total_chunks']}")
            return True
        except FileNotFoundError:
            print(f"[DEBUG] Database not found at {db_path}")
            self.stats["vector_store_loaded"] = False
            return False
        except Exception as e:
            print(f"[DEBUG] Database load error: {e}")
            self.stats["vector_store_loaded"] = False
            return False

    def get_retriever(self):
        """ドキュメントリトリーバーを取得.

        Returns:
            リトリーバーオブジェクト

        """
        if self.vector_store:
            return self.vector_store.as_retriever(
                search_kwargs={"k": self.config.rag.search_k}
            )
        return None

    async def check_lm_studio(self) -> bool:
        """LM Studioへの接続を確認.

        Returns:
            bool: 接続できた場合はTrue

        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.lm_studio.url}/models",
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and len(data["data"]) > 0:
                        self.stats["lm_connected"] = True
                        self.stats["model"] = data["data"][0]["id"]
                        return True
            return False
        except Exception:
            self.stats["lm_connected"] = False
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得.

        Returns:
            統計情報

        """
        return self.stats.copy()

    def update_statistics(self, stats: Dict[str, Any]) -> None:
        """統計情報を更新.

        Args:
            stats: 更新する統計情報

        """
        self.stats.update(stats)