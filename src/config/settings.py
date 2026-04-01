"""設定管理モジュール
CodeSentinelアプリケーションの設定を管理します。.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict


@dataclass
class AppSettings:
    """アプリケーション設定."""

    name: str = "CodeSentinel"
    version: str = "0.4.0"
    storage_secret: str = "sentinel_secret_key"
    mode: str = "Normal"  # モード設定を追加


@dataclass
class PathSettings:
    """パス設定."""

    target_dir: str = r"E:\sample\json"
    doc_dir: str = ""
    db_path: str = "faiss_index_code"
    chat_dir_path: Path = field(default_factory=lambda: Path("chat_history"))
    todo_dir_path: Path = field(default_factory=lambda: Path("todo_history"))

    def __post_init__(self):
        """パスの初期化処理."""
        self.chat_dir_path.mkdir(exist_ok=True)
        self.todo_dir_path.mkdir(exist_ok=True)

    @property
    def db_full_path(self) -> Path:
        """データベースのフルパス."""
        return Path(self.db_path)

    def get_target_dir(self) -> Path:
        """ターゲットディレクトリのPathオブジェクトを取得."""
        return Path(self.target_dir)

    def get_doc_dir(self) -> Path:
        """ドキュメントディレクトリのPathオブジェクトを取得."""
        return Path(self.doc_dir) if self.doc_dir else Path()

    @property
    def chat_dir(self) -> Path:
        """チャットディレクトリのPathオブジェクトを取得."""
        return self.chat_dir_path

    @property
    def todo_dir(self) -> Path:
        """ToDoディレクトリのPathオブジェクトを取得."""
        return self.todo_dir_path


@dataclass
class LMStudioSettings:
    """LM Studio設定."""

    url: str = "http://localhost:1234/v1"
    api_key: str = "lm-studio"
    timeout: float = 30.0
    check_embedding_ctx_length: bool = False

    def get_models_url(self) -> str:
        """モデル情報取得用URLを取得."""
        return f"{self.url}/models"


@dataclass
class RAGSettings:
    """RAG設定."""

    chunk_size_code: int = 1200
    chunk_overlap_code: int = 200
    chunk_size_doc: int = 1000
    chunk_overlap_doc: int = 100
    search_k: int = 10
    temperature: float = 0.1

    @property
    def code_separators(self) -> list:
        """コード分割用のセパレータ."""
        return ["\nclass ", "\ndef ", "\nvoid ", "\nint ", "\nstatic ", "\n\n", "\n", " ", ""]

    @property
    def doc_separators(self) -> list:
        """ドキュメント分割用のセパレータ."""
        return ["\n\n", "\n", " ", ""]

    @property
    def supported_extensions(self) -> set:
        """サポートするファイル拡張子."""
        return {".py", ".cs", ".cpp", ".h", ".hpp", ".json", ".pdf", ".md", ".xlsx", ".pptx", ".txt"}


@dataclass
class UISettings:
    """UI設定."""

    max_file_display: int = 10000
    max_document_chunks: int = 50000
    memory_threshold_percent: int = 90
    refresh_interval_seconds: int = 3

    @property
    def memory_threshold_bytes(self) -> float:
        """メモリ閾値（バイト）."""
        return self.memory_threshold_percent / 100.0


@dataclass
class Settings:
    """全設定を管理するメインクラス."""

    app: AppSettings = field(default_factory=AppSettings)
    paths: PathSettings = field(default_factory=PathSettings)
    lm_studio: LMStudioSettings = field(default_factory=LMStudioSettings)
    rag: RAGSettings = field(default_factory=RAGSettings)
    ui: UISettings = field(default_factory=UISettings)

    @classmethod
    def from_env(cls) -> 'Settings':
        """環境変数から設定を読み込む."""
        return cls()

    def update_from_user_storage(self, user_storage: dict) -> None:
        """ユーザーストレージの設定で更新する."""
        if 'target_dir' in user_storage:
            self.paths.target_dir = user_storage['target_dir']
        if 'doc_dir' in user_storage:
            self.paths.doc_dir = user_storage['doc_dir']
        if 'mode' in user_storage:
            self.app.mode = user_storage['mode']

    def to_user_storage(self) -> dict:
        """ユーザーストレージ用の設定を返す."""
        return {
            'target_dir': self.paths.target_dir,
            'doc_dir': self.paths.doc_dir,
            'mode': self.app.mode
        }


# グローバル設定インスタンス
settings: Settings = Settings.from_env()