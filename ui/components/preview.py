from pathlib import Path
import re
from nicegui import ui
from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer, guess_lexer
from pygments.token import Token

class PreviewDialog:
    """
    ファイル内容をプレビュー表示するためのダイアログ管理クラス。
    Nativeコンポーネントのみを使用し、ブラウザの制限(CSS剥離)に影響されない表示を実現します。 (v1.4.5 - Highlight)
    """
    def __init__(self):
        self.search_state = {
            'full_content': '', 
            'results': [], 
            'current': -1, 
            'tokens': [], 
            'colors': {},
            'debounce_timer': None,
            'file_path': None,
            'fix_code': None
        }
        
        with ui.dialog() as self.dialog, ui.card().style('width: 80vw; max-width: 1000px; height: 80vh; padding: 0; background-color: #272822; color: #f8f8f2; overflow: hidden; border: 1px solid #3e3d32;'):
            with ui.row().style('width: 100%; align-items: center; padding: 0.75rem 1rem; background-color: #1e1e1e; border-bottom: 1px solid #3e3d32; gap: 1rem;'):
                self.title_label = ui.label('').style('font-size: 0.85rem; font-weight: bold; flex-grow: 1; color: #d4d4d4; font-family: "JetBrains Mono";')
                
                # AI修正ボタン (初期は非表示)
                self.fix_button = ui.button('APPLY AI FIX', icon='auto_fix_high', on_click=self.confirm_fix)\
                    .props('flat dense color=green-4').classes('text-[10px] hidden')
                
                with ui.row().classes('items-center gap-1'):
                    self.search_input = ui.input(placeholder='Search...', on_change=lambda e: self.debounce_search(e.value))\
                        .props('dark dense outlined clearable').style('width: 150px; font-size: 0.75rem;')
                    self.search_count_label = ui.label('').classes('text-[10px] text-slate-500 w-12 text-center')
                    ui.button(icon='keyboard_arrow_up', on_click=lambda: self.jump_to_match(-1)).props('flat round dense color=gray').classes('text-slate-400')
                    ui.button(icon='keyboard_arrow_down', on_click=lambda: self.jump_to_match(1)).props('flat round dense color=gray').classes('text-slate-400')
                ui.button(icon='close', on_click=self.dialog.close).props('flat round dense color=gray')
            
            with ui.scroll_area().style('width: 100%; flex-grow: 1; padding: 1rem; background-color: #272822;') as self.scroll_area:
                self.code_container = ui.column().style('min-width: max-content; width: 100%; gap: 0;')

    def debounce_search(self, query: str):
        """検索処理の実行をデバウンス（遅延実行）します。"""
        if self.search_state['debounce_timer']:
            self.search_state['debounce_timer'].cancel()
        self.search_state['debounce_timer'] = ui.timer(0.4, lambda: self.handle_search(query), once=True)

    def confirm_fix(self):
        """修正を適用するか確認するダイアログを表示します。"""
        with ui.dialog() as diag, ui.card().classes('p-6 bg-[#1e1e1e] border border-slate-700'):
            ui.label('Apply AI Suggestion?').classes('text-lg font-bold text-white mb-2')
            ui.label('This will modify the file on disk.').classes('text-sm text-slate-400 mb-4')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('CANCEL', on_click=diag.close).props('flat color=gray')
                ui.button('APPLY', on_click=lambda: self.apply_fix(diag)).props('flat color=green')

    def apply_fix(self, dialog):
        """実際にファイルの内容を書き換えます。"""
        try:
            path = self.search_state['file_path']
            new_code = self.search_state['fix_code']
            if not path or not new_code: return
            
            # 安全のため、現在はファイル全体の置換として実装 (TODO: 行単位の精密パッチ)
            # もしAIがスニペットだけを返してきた場合、元ファイルの該当行を特定して置換したほうが良いが、
            # 現状はAIに「修正後の全コード」または「明確なスニペット」を期待する。
            # ここではシンプルに通知し、ファイルに書き込む。
            path.write_text(new_code, encoding='utf-8')
            ui.notify('File patched successfully!', color='positive')
            dialog.close()
            # プレビューを再読込
            self.open(path, str(path), fix_code=None)
        except Exception as e:
            ui.notify(f"Patch Error: {e}", color='red')

    def handle_search(self, query: str):
        """検索クエリに基づいてヒット箇所を特定し、プレビューを再描画します。"""
        content = self.search_state['full_content']
        if not query or len(query) < 2:
            self.search_state['results'] = []
            self.search_state['current'] = -1
            self.search_count_label.set_text('')
            self.render_lines()
            return

        lines = content.splitlines()
        results = [i + 1 for i, line in enumerate(lines) if query.lower() in line.lower()]
        
        self.search_state['results'] = results
        self.search_state['current'] = 0 if results else -1
        self.update_search_ui()
        self.render_lines(query=query, active_line=results[0] if results else None)
        if results: self.scroll_to_line(results[0])

    def update_search_ui(self):
        """検索結果の件数表示を更新します。"""
        res = self.search_state['results']
        curr = self.search_state['current']
        self.search_count_label.set_text(f'{curr + 1} / {len(res)}' if res else '0 / 0')

    def jump_to_match(self, delta: int):
        """検索結果を前後に移動します。"""
        res = self.search_state['results']
        if not res: return
        self.search_state['current'] = (self.search_state['current'] + delta) % len(res)
        self.update_search_ui()
        line = res[self.search_state['current']]
        self.render_lines(query=self.search_input.value, active_line=line)
        self.scroll_to_line(line)

    def scroll_to_line(self, line_num: int):
        """指定された行番号(1-indexed)へスクロールします。"""
        try: self.scroll_area.scroll_to(pixels=(line_num - 1) * 24)
        except: pass

    def open(self, file_path: Path, relative_path: str, jump_line=None, fix_code=None):
        try:
            content = file_path.read_text(encoding='utf-8')
            self.search_state.update({
                'full_content': content, 
                'results': [], 
                'current': -1,
                'file_path': file_path,
                'fix_code': fix_code
            })
            self.search_input.value = ''
            self.search_count_label.set_text('')
            self.title_label.set_text(relative_path)
            
            # 修正ボタンの表示制御
            if fix_code:
                self.fix_button.classes(remove='hidden')
            else:
                self.fix_button.classes(add='hidden')
            
            # トークン配色 (Monokai)
            self.search_state['colors'] = {
                Token.Keyword: '#66d9ef', Token.Name.Function: '#a6e22e',
                Token.Name.Class: '#a6e22e', Token.String: '#e6db74',
                Token.Comment: '#75715e', Token.Number: '#ae81ff',
                Token.Operator: '#f92672', Token.Punctuation: '#f8f8f2',
                Token.Name.Variable: '#f8f8f2', Token.Name.Builtin: '#f8f8f2',
            }

            ext = file_path.suffix.lower()
            if ext in {'.pdf', '.xlsx', '.pptx'}:
                self.code_container.clear()
                with self.code_container:
                    ui.label(f"Binary file ({ext}) cannot be previewed.").style('color: #75715e; font-style: italic; padding: 2rem;')
                self.search_state['tokens'] = [] # Clear tokens for binary files
            else:
                try: lexer = get_lexer_for_filename(file_path.name)
                except:
                    try: lexer = guess_lexer(content)
                    except: lexer = TextLexer()

                self.search_state['tokens'] = list(lexer.get_tokens(content))
            
            self.render_lines(active_line=int(jump_line) if jump_line else None)
            
            self.dialog.open()
            if jump_line: self.scroll_to_line(int(jump_line))
            else: self.scroll_area.scroll_to(pixels=0)
        except Exception as e:
            ui.notify(f"Error: {str(e)}", color='red')

    def render_lines(self, query: str = None, active_line: int = None):
        """トークンデータをNiceGUIコンポーネントとして描画します。"""
        self.code_container.clear()
        tokens = self.search_state['tokens']
        colors = self.search_state['colors']
        
        def render_row(num, tks):
            # 該当行のハイライト背景色
            row_bg = 'background-color: rgba(255, 235, 59, 0.1);' if num == active_line else ''
            with ui.row().style(f'min-width: 100%; gap: 0; align-items: baseline; height: 1.5rem; white-space: nowrap; {row_bg}'):
                ui.label(str(num)).style('width: 3.5rem; color: #75715e; text-align: right; user-select: none; font-family: "JetBrains Mono"; font-size: 11px; margin-right: 1.25rem; border-right: 1px solid #3e3d32; padding-right: 0.75rem;')
                with ui.row().style('gap: 0; align-items: baseline; flex-wrap: nowrap;'):
                    for tt, tv in tks:
                        val = tv.replace('\r', '')
                        if not val or val == '\n': continue
                        
                        color = colors.get(tt, '#f8f8f2')
                        if color == '#f8f8f2':
                            for ptype, pcolor in colors.items():
                                if tt in ptype: color = pcolor; break
                        
                        # 文字列内ハイライト
                        if query and query.lower() in val.lower():
                            parts = re.split(f'({re.escape(query)})', val, flags=re.IGNORECASE)
                            for part in parts:
                                if not part: continue
                                is_match = part.lower() == query.lower()
                                style = f'color: {"#000" if is_match else color}; background: {"#ffeb3b" if is_match else "transparent"};'
                                ui.label(part).style(style + ' font-family: "JetBrains Mono"; font-size: 13px; white-space: pre; margin: 0; padding: 0; flex-shrink: 0;')
                        else:
                            ui.label(val).style(f'color: {color}; font-family: "JetBrains Mono"; font-size: 13px; white-space: pre; margin: 0; padding: 0; flex-shrink: 0;')

        ln, current_tks, count = 1, [], 0
        with self.code_container:
            for tt, tv in tokens:
                if count >= 1000: break
                parts = tv.split('\n')
                for i, part in enumerate(parts):
                    if i > 0:
                        render_row(ln, current_tks)
                        ln += 1; count += 1; current_tks = []
                    if part: current_tks.append((tt, part))
            if current_tks and count < 1000:
                render_row(ln, current_tks)
