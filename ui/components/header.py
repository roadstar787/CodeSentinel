# ヘッダーUIコンポーネント
from nicegui import ui
from config import settings


def create_header(app_name: str = None, version: str = None, on_toggle_mode=None):
    """ヘッダーを作成する"""
    app_name = app_name or settings.app.name
    version = version or settings.app.version
    
    with ui.header().classes('bg-white text-slate-900 p-4 border-b flex justify-between shadow-none'):
        with ui.row().classes('items-center gap-4'):
            ui.button(icon='menu', on_click=lambda: ui.run_javascript('document.querySelector(".q-drawer").classList.toggle("q-drawer--shown")')).props('flat round color=slate-900')
            with ui.row().classes('items-baseline gap-2'):
                ui.label(app_name).classes('text-lg font-black uppercase')
                ui.label(f'v{version}').classes('text-[10px] font-mono text-slate-400')
        
        with ui.row().classes('items-center gap-2'):
            ui.label('MODE:').classes('text-[10px] text-slate-400')
            mode_toggle = ui.toggle({'Normal': 'Q&A', 'Gap': 'GAP'}, value='Normal', on_change=on_toggle_mode).props('dense unelevated toggle-color=indigo-600 color=slate-200 text-color=slate-600').classes('text-[10px]')