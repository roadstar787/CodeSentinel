"""プレビューダイアログUIコンポーネント"""

from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from nicegui import ui


# 検索状態の型
SearchState = Dict[str, Any]


def create_preview_dialog() -> Tuple[Callable[[], None], Callable[[str, Optional[str], Optional[int]], None]]:
    """プレビューダイアログを作成する.

    Returns:
        (get_dialog_func, open_preview) のタプル

    """
    # 検索状態の管理
    search_state: SearchState = {'last_query': '', 'last_index': -1, 'full_content': ''}
    
    # ダイアログインスタンスを保持
    dialog_instance: Optional[ui.dialog] = None

    def get_dialog() -> Optional[ui.dialog]:
        """ダイアログインスタンスを取得する.

        Returns:
            ui.dialog インスタンス（まだ作成されていない場合はNone）

        """
        return dialog_instance

    def open_preview(file_path: str, base_dir: Optional[str] = None, jump_line: Optional[int] = None) -> None:
        """プレビューダイアログを開く.

        Args:
            file_path: ファイルパス（相対パスまたは絶対パス）
            base_dir: 基準ディレクトリ
            jump_line: ジャンプする行番号（1始まり）

        """
        nonlocal dialog_instance
        
        if not file_path:
            return

        # 基準ディレクトリを決定
        base = base_dir if base_dir else '.'
        full_path = Path(base) / file_path

        if not full_path.is_file():
            ui.notify(f'File not found: {file_path}', color='red')
            return

        try:
            # ファイルの内容を読み込み
            try:
                content = full_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    content = full_path.read_text(encoding='cp932')
                except UnicodeDecodeError:
                    content = full_path.read_text(encoding='cp932', errors='replace')

            search_state['full_content'] = content
            search_state['last_index'] = -1

            # ファイル拡張子を取得
            ext = full_path.suffix.lower()[1:] or 'text'

            # ダイアログを表示
            with ui.dialog() as dialog, ui.card().classes('w-[90vw] max-w-5xl h-[85vh] p-0'):
                dialog_instance = dialog
                
                # ヘッダー
                with ui.row().classes('w-full items-center p-4 bg-slate-50 border-b gap-4'):
                    ui.label(file_path).classes('text-sm font-bold flex-grow text-slate-700')

                    # 検索入力
                    preview_search = ui.input(placeholder='Search...').props('dense outlined clearable').classes('w-48 text-xs')

                    # 閉じるボタン
                    ui.button(icon='close', on_click=dialog.close).props('flat round dense color=slate-400')

                # コード表示エリア
                with ui.scroll_area().classes('w-full flex-grow code-preview p-4'):
                    # PDFやExcelはテキストとして見れない場合は分岐
                    if ext in {'pdf', 'xlsx', 'pptx'}:
                        ui.label(f'Binary file ({ext}) cannot be previewed as text.').classes('text-slate-400 italic')
                    else:
                        lines = content.splitlines()
                        if lines:
                            ln_width = max(2, len(str(len(lines))))
                            ln_text = '\n'.join(str(i + 1) for i in range(len(lines)))

                            with ui.row().classes('w-full gap-0 items-start no-wrap'):
                                # 行番号列
                                ui.label(ln_text).classes('line-numbers-col text-xs').style(f'width: {ln_width + 2}ch; white-space: pre; font-family: monospace;')
                                # コード列
                                ui.code(content, language=ext).classes('code-col flex-grow text-xs bg-transparent p-0')

            dialog.open()

        except Exception as e:
            ui.notify(f'Read Error: {e}', color='red')

    return get_dialog, open_preview