"""
環境設定モジュール
環境変数とデフォルト値の定義を行います。
"""

import os
from typing import Dict, Any
from .config import Settings


class EnvSettings:
    """環境設定クラス"""
    
    # 環境変数のデフォルト値
    DEFAULTS = {
        'APP_NAME': 'CodeSentinel',
        'APP_VERSION': '0.4.0',
        'APP_STORAGE_SECRET': 'sentinel_secret_key',
        'TARGET_DIR': r'E:\sample\json',
        'DOC_DIR': '',
        'DB_PATH': 'faiss_index_code',
        'CHAT_DIR': 'chat_history',
        'LM_STUDIO_URL': 'http://localhost:1234/v1',
        'LM_STUDIO_API_KEY': 'lm-studio',
        'LM_STUDIO_TIMEOUT': '30.0',
        'LM_STUDIO_CHECK_EMBEDDING_CTX_LENGTH': 'false',
        'RAG_CHUNK_SIZE_CODE': '1200',
        'RAG_CHUNK_OVERLAP_CODE': '200',
        'RAG_CHUNK_SIZE_DOC': '1000',
        'RAG_CHUNK_OVERLAP_DOC': '100',
        'RAG_SEARCH_K': '10',
        'RAG_TEMPERATURE': '0.1',
        'UI_MAX_FILE_DISPLAY': '10000',
        'UI_MAX_DOCUMENT_CHUNKS': '50000',
        'UI_MEMORY_THRESHOLD_PERCENT': '90',
        'UI_REFRESH_INTERVAL_SECONDS': '3',
        'APP_MODE': 'Normal',
    }
    
    @classmethod
    def get_env_value(cls, key: str, default: Any = None) -> Any:
        """環境変数の値を取得"""
        return os.getenv(key, default or cls.DEFAULTS.get(key))
    
    @classmethod
    def get_bool_value(cls, key: str, default: bool = False) -> bool:
        """環境変数の値をboolで取得"""
        value = cls.get_env_value(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    @classmethod
    def get_int_value(cls, key: str, default: int = 0) -> int:
        """環境変数の値をintで取得"""
        try:
            return int(cls.get_env_value(key, str(default)))
        except ValueError:
            return default
    
    @classmethod
    def get_float_value(cls, key: str, default: float = 0.0) -> float:
        """環境変数の値をfloatで取得"""
        try:
            return float(cls.get_env_value(key, str(default)))
        except ValueError:
            return default
    
    @classmethod
    def update_settings_from_env(cls, settings: Settings) -> Settings:
        """環境変数から設定を更新"""
        # アプリケーション設定
        settings.app.name = cls.get_env_value('APP_NAME')
        settings.app.version = cls.get_env_value('APP_VERSION')
        settings.app.storage_secret = cls.get_env_value('APP_STORAGE_SECRET')
        settings.app.mode = cls.get_env_value('APP_MODE')
        
        # パス設定
        settings.paths.target_dir = cls.get_env_value('TARGET_DIR')
        settings.paths.doc_dir = cls.get_env_value('DOC_DIR')
        settings.paths.db_path = cls.get_env_value('DB_PATH')
        settings.paths.chat_dir_path = settings.paths.chat_dir_path
        
        # LM Studio設定
        settings.lm_studio.url = cls.get_env_value('LM_STUDIO_URL')
        settings.lm_studio.api_key = cls.get_env_value('LM_STUDIO_API_KEY')
        settings.lm_studio.timeout = cls.get_float_value('LM_STUDIO_TIMEOUT')
        settings.lm_studio.check_embedding_ctx_length = cls.get_bool_value('LM_STUDIO_CHECK_EMBEDDING_CTX_LENGTH')
        
        # RAG設定
        settings.rag.chunk_size_code = cls.get_int_value('RAG_CHUNK_SIZE_CODE')
        settings.rag.chunk_overlap_code = cls.get_int_value('RAG_CHUNK_OVERLAP_CODE')
        settings.rag.chunk_size_doc = cls.get_int_value('RAG_CHUNK_SIZE_DOC')
        settings.rag.chunk_overlap_doc = cls.get_int_value('RAG_CHUNK_OVERLAP_DOC')
        settings.rag.search_k = cls.get_int_value('RAG_SEARCH_K')
        settings.rag.temperature = cls.get_float_value('RAG_TEMPERATURE')
        
        # UI設定
        settings.ui.max_file_display = cls.get_int_value('UI_MAX_FILE_DISPLAY')
        settings.ui.max_document_chunks = cls.get_int_value('UI_MAX_DOCUMENT_CHUNKS')
        settings.ui.memory_threshold_percent = cls.get_int_value('UI_MEMORY_THRESHOLD_PERCENT')
        settings.ui.refresh_interval_seconds = cls.get_int_value('UI_REFRESH_INTERVAL_SECONDS')
        
        return settings
    
    @classmethod
    def get_all_env_settings(cls) -> Dict[str, str]:
        """すべての環境設定を取得"""
        return {key: cls.get_env_value(key) for key in cls.DEFAULTS.keys()}