"""ベクトルストアリポジトリの実装
FAISSベクトルストアの操作を提供します.
"""

from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from src.config.settings import Settings
from src.interfaces.repositories import IVectorStore


class VectorStoreRepository(IVectorStore):
    """ベクトルストアリポジトリの実装クラス."""

    def __init__(self, config: Settings, vectorstore: Optional[FAISS] = None):
        """初期化.

        Args:
            config: 設定オブジェクト
            vectorstore: FAISSインスタンス

        """
        self.config = config
        self.vectorstore = vectorstore
        self._embeddings = OpenAIEmbeddings(
            base_url=config.lm_studio.url,
            api_key=config.lm_studio.api_key,  # type: ignore[arg-type]
            check_embedding_ctx_length=config.lm_studio.check_embedding_ctx_length
        )

    @classmethod
    def load_local(
        cls,
        db_path: str,
        config: Settings,
        allow_dangerous_deserialization: bool = False
    ) -> "VectorStoreRepository":
        """ローカルからベクトルストアをロード.

        Args:
            db_path: データベースパス
            config: 設定オブジェクト
            allow_dangerous_deserialization: 危険なデシリアライズを許可するか

        Returns:
            VectorStoreRepositoryインスタンス

        """
        embeddings = OpenAIEmbeddings(
            base_url=config.lm_studio.url,
            api_key=config.lm_studio.api_key,  # type: ignore[arg-type]
            check_embedding_ctx_length=config.lm_studio.check_embedding_ctx_length
        )
        vectorstore = FAISS.load_local(
            db_path,
            embeddings,
            allow_dangerous_deserialization=allow_dangerous_deserialization
        )
        return cls(config, vectorstore)

    @classmethod
    def from_documents(
        cls,
        documents: List[Document],
        config: Settings
    ) -> "VectorStoreRepository":
        """ドキュメントからベクトルストアを作成（バッチ処理）.

        Args:
            documents: ドキュメントリスト
            config: 設定オブジェクト

        Returns:
            VectorStoreRepositoryインスタンス

        """
        print(f"[DEBUG] [Thread] FAISS Building started (Total: {len(documents)} units)...")
        embeddings = OpenAIEmbeddings(
            base_url=config.lm_studio.url,
            api_key=config.lm_studio.api_key,  # type: ignore[arg-type]
            check_embedding_ctx_length=config.lm_studio.check_embedding_ctx_length
        )
        print(f"[DEBUG] [Thread] Using Embeddings URL: {config.lm_studio.url}")

        # バッチサイズを小さく設定（LM Studioの負荷軽減）
        batch_size = 10
        total = len(documents)

        # テキストとメタデータを抽出
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        # 最初のバッチでインスタンスを作成
        first_batch_texts = texts[:batch_size]
        first_batch_metadatas = metadatas[:batch_size]
        print(f"[DEBUG] [Thread] Processing first batch (1-{min(batch_size, total)})")
        vectorstore = FAISS.from_texts(
            texts=first_batch_texts,
            embedding=embeddings,
            metadatas=first_batch_metadatas
        )

        # 残りのバッチを追加
        for i in range(batch_size, total, batch_size):
            batch_texts = texts[i: i + batch_size]
            batch_metadatas = metadatas[i: i + batch_size]
            current_count = i + len(batch_texts)
            print(f"[DEBUG] [Thread] Adding batch ({i + 1}-{current_count}) / {total}")
            vectorstore.add_texts(
                texts=batch_texts,
                metadatas=batch_metadatas
            )

        print(f"[DEBUG] [Thread] FAISS Building finished.")
        return cls(config, vectorstore)

    def save_local(self, db_path: str) -> None:
        """ベクトルストアをローカルに保存.

        Args:
            db_path: 保存先パス

        """
        if self.vectorstore:
            self.vectorstore.save_local(db_path)

    def as_retriever(self, search_kwargs: Optional[Dict[str, Any]] = None) -> Any:
        """リトリーバーとして取得.

        Args:
            search_kwargs: 検索パラメータ

        Returns:
            リトリーバーオブジェクト

        """
        if self.vectorstore:
            return self.vectorstore.as_retriever(search_kwargs=search_kwargs or {})
        return None

    @property
    def index(self) -> Any:
        """ベクトルストアのインデックスを取得.

        Returns:
            インデックスオブジェクト

        """
        return self.vectorstore.index if self.vectorstore else None