# プレビューダイアログUIコンポーネント
from nicegui import ui
from pathlib import Path


def create_preview_dialog():
    """プレビューダイアログを作成する"""
    with ui.dialog() as preview_dialog, ui.card().classes('w-[80vw] max-w-4xl h-[80vh] p-0') as card:
        with ui.row().classes('w-full items-center p-4 bg-slate-50 border-b gap-4'):
            # プレビューダイアログのタイトル
            preview_title = ui.label('').classes('text-sm font-bold flex-grow text-slate-700')
            # 検索入力
            preview_search = ui.input(placeholder='Search...').props('dense outlined clearable').classes('w-48 text-xs')
            preview_search.on('keydown.enter', lambda: search_in_preview())
            ui.button(icon='search', on_click=lambda: search_in_preview()).props('flat round dense color=slate-400')
            # ダイアログを閉じるボタン
            ui.button(icon='close', on_click=preview_dialog.close).props('flat round dense color=slate-400')
        
        # プレビューするコードを表示するスクロール可能なエリア
        with ui.scroll_area().classes('w-full flex-grow code-preview p-4') as preview_scroll:
            # コード表示用コンテナ (動的に再生成するため)
            preview_code_box = ui.column().classes('w-full')

    # プレビュー内検索の状態管理
    search_state = {'last_query': '', 'last_index': -1, 'full_content': ''}

    def search_in_preview():
        query = str(preview_search.value or "").strip()
        if not query: return
        content = str(search_state.get('full_content', ""))
        if not content: return
        lines = content.splitlines()
        
        # 次のヒット箇所を探す (循環検索)
        last_idx = int(search_state.get('last_index', -1))
        last_q = str(search_state.get('last_query', ""))
        start_idx = last_idx + 1 if query == last_q else 0
        
        found_idx = -1
        matches = [idx for idx, line in enumerate(lines) if query.lower() in line.lower()]
        total = len(matches)
        
        if total > 0:
            # 次のインデックスを計算
            if query == last_q:
                # すでにヒットしている場合、次のマッチを探す
                next_matches = [m for m in matches if m > last_idx]
                found_idx = next_matches[0] if next_matches else matches[0]
                match_no = matches.index(found_idx) + 1
            else:
                found_idx = matches[0]
                match_no = 1

            # ヒット！スクロール実行
            line_height = 20 
            preview_scroll.scroll_to(pixels=found_idx * line_height)
            
            search_state['last_index'] = found_idx
            search_state['last_query'] = query
            ui.notify(f"Match {match_no}/{total} (Line {found_idx + 1})", color='indigo', pos='top', duration=1000)
        else:
            ui.notify("No matches found", color='orange', pos='top')
            search_state['last_index'] = -1

    def open_preview(file_path, base_dir=None, jump_line=None):
        # ファイルパスが指定されていなければ何もしない
        if not file_path: return
        # 基準ディレクトリを決定
        base = base_dir if base_dir else "."
        # フルパスを作成
        full_path = Path(base) / file_path
        # フルパスがファイルでなければ何もしない
        if not full_path.is_file(): return
        try:
            # ファイルの内容を読み込み (UTF-8 -> CP932 -> CP932 with replace)
            try:
                content = full_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    content = full_path.read_text(encoding='cp932')
                except UnicodeDecodeError:
                    content = full_path.read_text(encoding='cp932', errors='replace')
            
            search_state['full_content'] = content
            search_state['last_index'] = -1
            # プレビュータイトルを設定
            preview_title.set_text(f"{file_path}")
            # 言語指定 (ファイル拡張子に基づいてシンタックスハイライト)
            ext = full_path.suffix.lower()[1:] or 'text'
            
            preview_code_box.clear()
            with preview_code_box:
                # PDFやExcelはテキストとして見れない場合があるので分岐
                if ext in {'pdf', 'xlsx', 'pptx'}:
                    ui.label(f"Binary file ({ext}) cannot be previewed as text.").classes('text-slate-400 italic')
                else:
                    lines = content.splitlines()
                    ln_width = max(2, len(str(len(lines))))
                    ln_text = "\n".join(str(i+1) for i in range(len(lines)))
                    
                    with ui.row().classes('w-full gap-0 items-start no-wrap'):
                        # 行番号列
                        ui.label(ln_text).classes('line-numbers-col jetbrains-mono text-xs').style(f'width: {ln_width + 2}ch; white-space: pre;')
                        # コード列
                        ui.code(content, language=ext).classes('code-col flex-grow jetbrains-mono text-xs bg-transparent p-0')
            
            # プレビューダイアログを開く
            preview_dialog.open()
            
            # 指定行があればスクロール
            if jump_line is not None:
                try:
                    line_idx = int(jump_line) - 1
                    line_height = 20
                    # ダイアログが開くのを少し待ってからスクロール
                    ui.timer(0.2, lambda: preview_scroll.scroll_to(pixels=line_idx * line_height), once=True)
                except: pass
            else:
                preview_scroll.scroll_to(pixels=0)
        except Exception as e:
            # ファイル読み込みエラーを通知
            ui.notify(f"Read Error: {e}", color='red')

    return preview_dialog, open_preview