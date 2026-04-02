"""ドキュメントサービスモジュール
ドキュメント関連のビジネスロジックを管理します.
"""

from typing import Any, Dict, Optional

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
            "model": "N/A"
        }

    async def rebuild_database(self) -> tuple[bool, str]:
        """ベクトルストアを再構築.

        Returns:
            tuple[成功フラグ, メッセージ]

        """
        processor = DocumentProcessor(self.config)
        success, message = await processor.process_all_documents()

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
        self.stats["total_chunks"] = len(documents)
        self.stats["last_rebuild"] = "Just now"

        return True, f"Indexed {len(documents)} chunks"

    def load_database(self) -> bool:
        """FAISSベクトルストアをロード.

        Returns:
            bool: ロードできた場合はTrue

        """
        try:
            db_path = str(self.config.paths.db_full_path)
            self.vector_store = VectorStoreRepository.load_local(db_path, self.config)
            return True
        except (FileNotFoundError, Exception):
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