from pathlib import Path
from nicegui import ui

class PreviewDialog:
    def __init__(self):
        self.search_state = {'last_query': '', 'last_index': -1, 'full_content': ''}
        
        with ui.dialog() as self.dialog, ui.card().classes('w-[80vw] max-w-4xl h-[80vh] p-0'):
            with ui.row().classes('w-full items-center p-4 bg-slate-50 border-b gap-4'):
                self.title_label = ui.label('').classes('text-sm font-bold flex-grow text-slate-700')
                self.search_input = ui.input(placeholder='Search...').props('dense outlined clearable').classes('w-48 text-xs')
                self.search_input.on('keydown.enter', self.search_in_preview)
                ui.button(icon='search', on_click=self.search_in_preview).props('flat round dense color=slate-400')
                ui.button(icon='close', on_click=self.dialog.close).props('flat round dense color=slate-400')
            
            with ui.scroll_area().classes('w-full flex-grow code-preview p-4') as self.scroll_area:
                self.code_container = ui.column().classes('w-full')

    def search_in_preview(self):
        query = str(self.search_input.value or "").strip()
        if not query: return
        content = self.search_state.get('full_content', "")
        if not content: return
        lines = content.splitlines()
        
        last_idx = self.search_state.get('last_index', -1)
        last_q = self.search_state.get('last_query', "")
        
        matches = [idx for idx, line in enumerate(lines) if query.lower() in line.lower()]
        total = len(matches)
        
        if total > 0:
            if query == last_q:
                next_matches = [m for m in matches if m > int(last_idx)]
                found_idx = next_matches[0] if next_matches else matches[0]
                match_no = matches.index(found_idx) + 1
            else:
                found_idx = matches[0]
                match_no = 1

            self.scroll_area.scroll_to(pixels=found_idx * 20)
            self.search_state['last_index'] = found_idx
            self.search_state['last_query'] = query
            ui.notify(f"Match {match_no}/{total} (Line {found_idx + 1})", color='indigo', pos='top', duration=1000)
        else:
            ui.notify("No matches found", color='orange', pos='top')
            self.search_state['last_index'] = -1

    def open(self, file_path: Path, relative_path: str, jump_line=None):
        try:
            content = file_path.read_text(encoding='utf-8')
            self.search_state['full_content'] = content
            self.search_state['last_index'] = -1
            self.title_label.set_text(relative_path)
            
            ext = file_path.suffix.lower()[1:] or 'text'
            self.code_container.clear()
            
            with self.code_container:
                if ext in {'pdf', 'xlsx', 'pptx'}:
                    ui.label(f"Binary file ({ext}) cannot be previewed as text.").classes('text-slate-400 italic')
                else:
                    lines = content.splitlines()
                    ln_width = max(2, len(str(len(lines))))
                    ln_text = "\n".join(str(i+1) for i in range(len(lines)))
                    
                    with ui.row().classes('w-full gap-0 items-start no-wrap'):
                        ui.label(ln_text).classes('line-numbers-col jetbrains-mono text-xs').style(f'width: {ln_width + 2}ch; white-space: pre;')
                        ui.code(content, language=ext).classes('code-col flex-grow jetbrains-mono text-xs bg-transparent p-0')
            
            self.dialog.open()
            if jump_line is not None:
                try:
                    line_idx = int(jump_line) - 1
                    ui.timer(0.2, lambda: self.scroll_area.scroll_to(pixels=line_idx * 20), once=True)
                except: pass
            else:
                self.scroll_area.scroll_to(pixels=0)
        except Exception as e:
            ui.notify(f"Read Error: {e}", color='red')
