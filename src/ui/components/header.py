"""ヘッダーUIコンポーネント"""

from typing import Any, Callable, Optional

from nicegui import ui


def create_header(
    app_name: str = "CodeSentinel",
    version: str = "0.4.0",
    drawer: Optional[Any] = None,
    on_toggle_mode: Optional[Callable] = None,
) -> ui.toggle:
    """ヘッダーを作成する.

    Args:
        app_name: アプリケーション名
        version: バージョン
        drawer: サイドバーのdrawerオブジェクト
        on_toggle_mode: モード切り替え時のコールバック

    Returns:
        モード切り替えトグルオブジェクト

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

        with ui.row().classes('items-center gap-2'):
            ui.label('MODE:').classes('text-[10px] text-slate-400')
            mode_toggle = ui.toggle(
                {'Normal': 'Q&A', 'Gap': 'GAP'},
                value='Normal',
                on_change=on_toggle_mode,
            ).props('dense unelevated toggle-color=indigo-600 color=slate-200 text-color=slate-600').classes('text-[10px]')

    return mode_toggle
