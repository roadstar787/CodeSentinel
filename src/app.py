"""CodeSentinel v2.0 アプリケーションエントリーポイント"""

from nicegui import ui, app

from src.config.settings import Settings
from src.core.backend import RAGBackend
from src.ui.main_page import create_main_ui


def init_backend() -> RAGBackend:
    """バックエンドを初期化する."""
    config = Settings()
    return RAGBackend(config)


@ui.page('/')
def index() -> None:
    """メインページ."""
    backend = app.storage.general.get('backend')
    if backend:
        create_main_ui(backend)
    else:
        ui.label('バックエンドが初期化されていません').classes('text-red-500')


def main() -> None:
    """アプリケーションを起動する."""
    # バックエンドを初期化してストレージに保存
    backend = init_backend()
    app.storage.general['backend'] = backend

    # NiceGUIを起動
    ui.run(
        title='CodeSentinel v2.0',
        favicon='🛡️',
        dark=True,
        storage_secret='codesentinel-secret-key'
    )


if __name__ == '__main__':
    main()