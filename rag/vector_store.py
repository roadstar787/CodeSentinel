"""
ベクトルストア管理モジュール
FAISSベクトルストアの操作を管理します。
"""

import os
from typing import List, Optional, Any
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


class VectorStoreManager:
    """ベクトルストアを管理するクラス"""
    
    def __init__(self, config, vectorstore: Optional[FAISS] = None):
        """
        初期化
        
        Args:
            config: 設定オブジェクト
            vectorstore: FAISSインスタンス
        """
        self.config = config
        self.vectorstore = vectorstore
        self.embeddings = OpenAIEmbeddings(
            base_url=self.config.lm_studio.url,
            api_key=self.config.lm_studio.api_key,
            check_embedding_ctx_length=self.config.lm_studio.check_embedding_ctx_length
        )
    
    @classmethod
    def load_local(cls, db_path: str, config, allow_dangerous_deserialization: bool = False) -> 'VectorStoreManager':
        """
        ローカルからベクトルストアをロード
        
        Args:
            db_path: データベースパス
            config: 設定オブジェクト
            allow_dangerous_deserialization: 危険なデシリアライズを許可するか
            
        Returns:
            VectorStoreManagerインスタンス
        """
        embeddings = OpenAIEmbeddings(
            base_url=config.lm_studio.url,
            api_key=config.lm_studio.api_key,
            check_embedding_ctx_length=config.lm_studio.check_embedding_ctx_length
        )
        vectorstore = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=allow_dangerous_deserialization)
        return cls(config, vectorstore)
    
    def save_local(self, db_path: str):
        """
        ベクトルストアをローカルに保存
        
        Args:
            db_path: 保存先パス
        """
        if self.vectorstore:
            self.vectorstore.save_local(db_path)
    
    def as_retriever(self, search_kwargs: Optional[dict] = None):
        """
        リトリーバーとして取得
        
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
        """
        ベクトルストアのインデックスを取得
        
        Returns:
            インデックスオブジェクト
        """
        return self.vectorstore.index if self.vectorstore else None