from nicegui import ui

def create_header(drawer_toggle_func, app_name, app_version, backend_stats, mode_toggle_func):
    with ui.header().classes('bg-white text-slate-900 p-4 border-b flex justify-between shadow-none'):
        with ui.row().classes('items-center gap-4'):
            ui.button(icon='menu', on_click=drawer_toggle_func).props('flat round color=slate-900')
            with ui.row().classes('items-baseline gap-2'):
                ui.label(app_name).classes('text-lg font-black uppercase')
                ui.label(f'v{app_version}').classes('text-[10px] font-mono text-slate-400')
        with ui.row().classes('items-center gap-2'):
            ui.label('MODE:').classes('text-[10px] text-slate-400')
            m_toggle = ui.toggle({'Normal': 'Q&A', 'Gap': 'GAP'}, value=backend_stats["mode"], on_change=lambda e: mode_toggle_func(e.value)).props('dense unelevated toggle-color=indigo-600 color=slate-200 text-color=slate-600').classes('text-[10px]')
            idx_label = ui.label(f'IDX: {backend_stats["total_chunks"]}').classes('text-[10px] font-mono text-slate-500')
    return m_toggle, idx_label

def create_footer(handle_query_func):
    with ui.footer().classes('bg-transparent'):
        with ui.row().classes('w-full max-w-4xl mx-auto p-4 bg-white border border-slate-300 items-end gap-2 shadow-lg rounded-t-xl'):
            input_field = ui.textarea(placeholder='Ask...').classes('flex-grow text-sm').props('borderless autogrow')
            ui.button(on_click=handle_query_func).props('flat icon=send color=indigo-600')
    return input_field
