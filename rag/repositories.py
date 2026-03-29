"""
リポジトリ層の実装
データアクセスロジックをカプセル化します。
"""

import os
import json
from typing import List, Optional, Any
from pathlib import Path
from abc import ABC, abstractmethod

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from .interfaces import IVectorStore, IFileStorage, IEmbeddingService, IJsonRepository


class VectorStoreRepository(IVectorStore):
    """ベクトルストアリポジトリの実装"""
    
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
            base_url=config.lm_studio.url,
            api_key=config.lm_studio.api_key,
            check_embedding_ctx_length=config.lm_studio.check_embedding_ctx_length
        )
    
    @classmethod
    def load_local(cls, db_path: str, config, allow_dangerous_deserialization: bool = False) -> 'VectorStoreRepository':
        """
        ローカルからベクトルストアをロード
        
        Args:
            db_path: データベースパス
            config: 設定オブジェクト
            allow_dangerous_deserialization: 危険なデシリアライズを許可するか
            
        Returns:
            VectorStoreRepositoryインスタンス
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


class FileStorageRepository(IFileStorage):
    """ファイルストレージリポジトリの実装"""
    
    def exists(self, path: str) -> bool:
        """ファイルが存在するか確認"""
        return os.path.exists(path)
    
    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """テキストファイルを読み込む"""
        with open(path, "r", encoding=encoding) as f:
            return f.read()
    
    def write_text(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """テキストファイルを書き込む"""
        # ディレクトリが存在しない場合は作成
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding=encoding) as f:
            f.write(content)
    
    def delete(self, path: str) -> bool:
        """ファイルを削除"""
        try:
            if os.path.exists(path):
                os.remove(path)
                return True
            return False
        except Exception:
            return False
    
    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """ディレクトリ内のファイルをリストアップ"""
        try:
            path = Path(directory)
            if path.is_dir():
                return [str(p) for p in path.glob(pattern) if p.is_file()]
            return []
        except Exception:
            return []
    
    def mkdir(self, path: str, exist_ok: bool = True) -> None:
        """ディレクトリを作成"""
        Path(path).mkdir(parents=True, exist_ok=exist_ok)


class EmbeddingService(IEmbeddingService):
    """埋め込みサービスの実装"""
    
    def __init__(self, config):
        """
        初期化
        
        Args:
            config: 設定オブジェクト
        """
        self.config = config
        self.embeddings = OpenAIEmbeddings(
            base_url=config.lm_studio.url,
            api_key=config.lm_studio.api_key,
            check_embedding_ctx_length=config.lm_studio.check_embedding_ctx_length
        )
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """テキストの埋め込みベクトルを生成"""
        return self.embeddings.embed_documents(texts)
    
    def create_embedding(self, text: str) -> List[float]:
        """単一テキストの埋め込みベクトルを生成"""
        return self.embeddings.embed_query(text)


class JsonRepository(IJsonRepository):
    """JSONデータリポジトリの実装"""
    
    def __init__(self, file_storage: IFileStorage):
        """
        初期化
        
        Args:
            file_storage: ファイルストレージインスタンス
        """
        self.file_storage = file_storage
    
    def save(self, data: dict[str, Any], path: str) -> None:
        """JSONデータを保存"""
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        self.file_storage.write_text(path, json_str)
    
    def load(self, path: str) -> Optional[dict[str, Any]]:
        """JSONデータを読み込む"""
        if not self.file_storage.exists(path):
            return None
        
        try:
            json_str = self.file_storage.read_text(path)
            return json.loads(json_str)
        except (json.JSONDecodeError, Exception):
            return None
    
    def delete(self, path: str) -> bool:
        """JSONファイルを削除"""
        return self.file_storage.delete(path)
    
    def exists(self, path: str) -> bool:
        """JSONファイルが存在するか確認"""
        return self.file_storage.exists(path)