"""CodeSentinel v2.0 アプリケーションエントリーポイント"""

import warnings

from nicegui import ui, app

from src.config.settings import Settings
from src.core.backend import RAGBackend
from src.ui.main_page import create_main_ui

# 警告を抑制
warnings.filterwarnings("ignore", message="Parameters {'max_tokens'} should be specified explicitly")


def init_backend() -> RAGBackend:
    """バックエンドを初期化する."""
    config = Settings()
    return RAGBackend(config)


def main() -> None:
    """アプリケーションを起動する."""
    # バックエンドを初期化
    backend = init_backend()

    @ui.page('/')
    def index() -> None:
        """メインページ."""
        create_main_ui(backend)

    # NiceGUIを起動
    ui.run(
        title='CodeSentinel v2.0',
        favicon='🛡️',
        dark=True,
        storage_secret='codesentinel-secret-key'
    )


if __name__ in {'__main__', '__mp_main__'}:
    main()
