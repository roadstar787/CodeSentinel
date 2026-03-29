"""
ドキュメント処理モジュール
ドキュメントの読み込み、前処理、チャンク分割を行います。
"""

import os
import asyncio
import psutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader, 
    PyPDFLoader, 
    UnstructuredMarkdownLoader, 
    UnstructuredExcelLoader, 
    UnstructuredPowerPointLoader
)

from config import Settings


@dataclass
class ProcessedDocument:
    """処理済みドキュメント"""
    content: str
    metadata: Dict[str, Any]


class DocumentProcessor:
    """ドキュメントを処理するクラス"""
    
    def __init__(self, config: Settings):
        """
        初期化
        
        Args:
            config: 設定オブジェクト
        """
        self.config = config
        self.processed_documents: List[ProcessedDocument] = []
        
        # ドキュメント分割設定
        self.code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.rag.chunk_size_code,
            chunk_overlap=config.rag.chunk_overlap_code,
            separators=config.rag.code_separators
        )
        
        self.doc_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.rag.chunk_size_doc,
            chunk_overlap=config.rag.chunk_overlap_doc,
            separators=config.rag.doc_separators
        )
    
    def get_document_loader(self, file_path: Path):
        """
        ファイルパスに基づいて適切なローダーを取得
        
        Args:
            file_path: ファイルパス
            
        Returns:
            ドキュメントローダー
        """
        ext = file_path.suffix.lower()
        
        if ext in {".py", ".cpp", ".h", ".hpp", ".cs", ".json"}:
            return TextLoader(str(file_path), encoding="utf-8")
        elif ext == ".pdf":
            return PyPDFLoader(str(file_path))
        elif ext == ".md":
            return UnstructuredMarkdownLoader(str(file_path))
        elif ext == ".xlsx":
            return UnstructuredExcelLoader(str(file_path))
        elif ext == ".pptx":
            return UnstructuredPowerPointLoader(str(file_path))
        else:
            raise ValueError(f"Unsupported file extension: {ext}")
    
    def split_documents(self, documents: List, doc_type: str = "code") -> List[ProcessedDocument]:
        """
        ドキュメントをチャンク分割
        
        Args:
            documents: ドキュメントリスト
            doc_type: ドキュメントタイプ ('code' または 'document')
            
        Returns:
            処理済みドキュメントリスト
        """
        splitter = self.code_splitter if doc_type == "code" else self.doc_splitter
        processed_docs = []
        
        for doc in documents:
            chunks = splitter.split_documents([doc])
            for chunk in chunks:
                processed_docs.append(ProcessedDocument(
                    content=chunk.page_content,
                    metadata=chunk.metadata
                ))
        
        return processed_docs
    
    def process_file(self, file_path: Path, base_path: Path, doc_type: str = "code") -> List[ProcessedDocument]:
        """
        単一ファイルを処理
        
        Args:
            file_path: ファイルパス
            base_path: ベースパス
            doc_type: ドキュメントタイプ
            
        Returns:
            処理済みドキュメントリスト
        """
        try:
            loader = self.get_document_loader(file_path)
            
            # テキストファイルの場合はエンコーディングのフォールバックを試行
            try:
                raw_documents = loader.load()
            except UnicodeDecodeError:
                if isinstance(loader, TextLoader):
                    # UTF-8で失敗した場合はCP932でリトライ
                    loader.encoding = "cp932"
                    raw_documents = loader.load()
                else:
                    raise
            
            # メタデータの追加
            for doc in raw_documents:
                doc.metadata["source"] = str(file_path.relative_to(base_path))
                doc.metadata["type"] = doc_type
            
            # チャンク分割
            return self.split_documents(raw_documents, doc_type)
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return []
    
    async def process_directory(self, dir_path: Path, base_path: Path, doc_type: str = "code") -> List[ProcessedDocument]:
        """
        ディレクトリ内のファイルを処理
        
        Args:
            dir_path: ディレクトリパス
            base_path: ベースパス
            doc_type: ドキュメントタイプ
            
        Returns:
            処理済みドキュメントリスト
        """
        if not dir_path.exists():
            return []
        
        # ファイル検索
        files = [
            p for p in dir_path.rglob('*') 
            if p.suffix.lower() in self.config.rag.supported_extensions 
            and ".venv" not in p.parts 
            and ".git" not in p.parts
        ]
        
        # ファイル数チェック
        if len(files) > self.config.ui.max_file_display:
            raise ValueError(f"Too many files ({len(files)}). Please reduce the number of files.")
        
        processed_docs = []
        
        for file_path in files:
            try:
                docs = self.process_file(file_path, base_path, doc_type)
                processed_docs.extend(docs)
                
                # メモリ使用量チェック
                mem = psutil.virtual_memory()
                if mem.percent > self.config.ui.memory_threshold_percent:
                    raise ValueError(f"High memory usage ({mem.percent}%). Please try with fewer files.")
                    
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
        
        return processed_docs
    
    async def process_all_documents(self) -> Tuple[bool, str]:
        """
        すべてのドキュメントを処理
        
        Returns:
            tuple[成功フラグ, メッセージ]
        """
        self.processed_documents = []
        all_docs = []
        
        # ターゲットディレクトリの処理
        target_dir = self.config.paths.get_target_dir()
        if target_dir.exists():
            target_docs = await self.process_directory(target_dir, target_dir, "code")
            all_docs.extend(target_docs)
        
        # ドキュメントディレクトリの処理
        doc_dir = self.config.paths.get_doc_dir()
        if doc_dir.exists():
            doc_docs = await self.process_directory(doc_dir, doc_dir, "document")
            all_docs.extend(doc_docs)
        
        if not all_docs:
            return False, "No documents found"
        
        # ドキュメント数チェック
        if len(all_docs) > self.config.ui.max_document_chunks:
            return False, f"Too many document chunks ({len(all_docs)}). Please reduce the number of files."
        
        self.processed_documents = all_docs
        return True, f"Processed {len(all_docs)} documents"
    
    def get_processed_documents(self) -> List[ProcessedDocument]:
        """
        処理済みドキュメントを取得
        
        Returns:
            処理済みドキュメントリスト
        """
        return self.processed_documents
    
    def clear_processed_documents(self):
        """処理済みドキュメントをクリア"""
        self.processed_documents = []