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
                
                # AI修正ボタンと表示切り替え (初期は非表示)
                with ui.row().classes('items-center gap-2') as self.fix_controls:
                    self.view_toggle = ui.toggle({
                        'original': 'ORIGINAL',
                        'fix': 'AI SUGGESTION'
                    }, value='original', on_change=self.handle_view_toggle).props('flat dense').classes('text-[10px]')
                    self.fix_button = ui.button('APPLY AI FIX', icon='auto_fix_high', on_click=self.confirm_fix)\
                        .props('flat dense color=green-4').classes('text-[10px]')
                self.fix_controls.classes('hidden')
                
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
        with ui.dialog() as diag:
            with ui.card().classes('p-6 bg-[#1e1e1e] border border-slate-700'):
                ui.label('AI修正の適用').classes('text-lg font-bold text-white mb-2')
                ui.label('この操作は元ファイルを直接書き換えます。よろしいですか？').classes('text-sm text-slate-400 mb-2')
                # スニペットに関する警告を追加
                with ui.row().classes('items-center gap-2 p-2 bg-amber-900/20 border border-amber-500/50 rounded mb-6'):
                    ui.icon('warning', color='amber-500')
                    ui.label('【注意】AIの提案がファイル全体ではなく「一部（スニペット）」の場合、ファイルを破壊する恐れがあります。差分をよく確認してください。').classes('text-[11px] text-amber-200 line-height-tight')
                
                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('キャンセル', on_click=diag.close).props('flat color=gray')
                    ui.button('適用する', on_click=lambda: self.apply_fix(diag)).props('flat color=green')
        diag.open()

    def apply_fix(self, dialog):
        """実際にファイルの内容を書き換えます。"""
        import os
        try:
            path = self.search_state['file_path']
            new_code = self.search_state['fix_code']
            if not path or not new_code:
                ui.notify("No fix code available.", color='warning')
                return
            
            # 修正案をファイルに書き込む (UTF-8)
            # 強制的にOSレベルで同期させる
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(new_code)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except:
                    pass # 一部のファイルシステムでは失敗する可能性があるため
            
            ui.notify(f'SUCCESS: {path.name} has been updated.', color='positive', icon='check_circle')
            dialog.close()
            # プレビューを再読込（修正後の内容を最新として表示）
            self.open(path, str(path), jump_line=None, fix_code=None)
        except Exception as e:
            print(f"[ERROR] Patch failed: {e}")
            ui.notify(f"Patch Error: {e}", color='red', icon='error')

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

    def handle_view_toggle(self):
        """表示モード（オリジナル/修正案）を切り替えます。"""
        mode = self.view_toggle.value
        self.search_state['tokens'] = self.search_state['fix_tokens'] if mode == 'fix' else self.search_state['orig_tokens']
        self.render_lines()

    def open(self, file_path: Path, relative_path: str, jump_line=None, fix_code=None, file_type='code'):
        try:
            self.search_state.update({
                'full_content': '', 
                'results': [], 
                'current': -1,
                'file_path': file_path,
                'fix_code': fix_code,
                'orig_tokens': [],
                'fix_tokens': []
            })
            self.search_input.value = ''
            self.search_count_label.set_text('')
            self.title_label.set_text(relative_path)
            
            # 表示モードの初期化
            self.view_toggle.value = 'original'
            
            # 修正ボタンの表示制御
            if fix_code:
                self.fix_controls.classes(remove='hidden')
            else:
                self.fix_controls.classes(add='hidden')
            
            ext = file_path.suffix.lower()
            if ext == '.pdf':
                self.code_container.clear()
                with self.code_container:
                    from urllib.parse import quote
                    safe_path = quote(relative_path.replace('\\', '/'))
                    url = f"/serve_file/{file_type}/{safe_path}"
                    with ui.row().classes('w-full justify-end p-2'):
                        ui.link('OPEN IN BROWSER', url, new_tab=True).classes('text-xs text-blue-400 underline')
                    ui.html(f'<iframe src="{url}" style="width: 100%; height: 75vh; border: none; background: white;"></iframe>').classes('w-full')
                self.search_state['tokens'] = []
            elif ext in {'.xlsx', '.pptx'}:
                self.code_container.clear()
                with self.code_container:
                    from urllib.parse import quote
                    safe_path = quote(relative_path.replace('\\', '/'))
                    url = f"/serve_file/{file_type}/{safe_path}"
                    with ui.row().classes('w-full justify-end p-2'):
                        ui.link('OPEN / DOWNLOAD', url, new_tab=True).classes('text-xs text-blue-400 underline')
                    ui.label(f"Binary file ({ext}) cannot be previewed within the browser.").style('color: #75715e; font-style: italic; padding: 2rem;')
                    ui.label("Please use the 'OPEN / DOWNLOAD' link above to view in your native application.").style('color: #75715e; font-size: 0.8rem; padding: 0 2rem;')
                self.search_state['tokens'] = []
            else:
                content = file_path.read_text(encoding='utf-8')
                self.search_state['full_content'] = content
                
                self.search_state['colors'] = {
                    Token.Keyword: '#66d9ef', Token.Name.Function: '#a6e22e',
                    Token.Name.Class: '#a6e22e', Token.String: '#e6db74',
                    Token.Comment: '#75715e', Token.Number: '#ae81ff',
                    Token.Operator: '#f92672', Token.Punctuation: '#f8f8f2',
                    Token.Name.Variable: '#f8f8f2', Token.Name.Builtin: '#f8f8f2',
                }

                try: lexer = get_lexer_for_filename(file_path.name)
                except:
                    try: lexer = guess_lexer(content)
                    except: lexer = TextLexer()

                # オリジナルと修正案の両方をトークン化
                self.search_state['orig_tokens'] = list(lexer.get_tokens(content))
                if fix_code:
                    self.search_state['fix_tokens'] = list(lexer.get_tokens(fix_code))
                
                # 表示モードの初期化
                if fix_code:
                    self.search_state['tokens'] = self.search_state['fix_tokens']
                    self.view_toggle.value = 'fix'
                else:
                    self.search_state['tokens'] = self.search_state['orig_tokens']
                    self.view_toggle.value = 'original'
                
                self.render_lines(active_line=int(jump_line) if jump_line else None)
            
            self.dialog.open()
            if not ext == '.pdf':
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
