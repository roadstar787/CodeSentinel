"""ヘッダーUIコンポーネント"""

from typing import Any, Optional

from nicegui import ui


def create_header(
    app_name: str = "CodeSentinel",
    version: str = "0.4.0",
    drawer: Optional[Any] = None,
) -> None:
    """ヘッダーを作成する.

    Args:
        app_name: アプリケーション名
        version: バージョン
        drawer: サイドバーのdrawerオブジェクト

    """
    with ui.header().classes('bg-white text-slate-900 p-4 border-b flex justify-between shadow-none'):
        with ui.row().classes('items-center gap-4'):
            if drawer is not None:
                ui.button(
                    icon='menu',
                    on_click=drawer.toggle,
                ).props('flat round').classes('text-slate-600')
            with ui.row().classes('items-baseline gap-2'):
                ui.label(app_name).classes('text-lg font-black uppercase')
                ui.label(f'v{version}').classes('text-[10px] font-mono text-slate-400')
