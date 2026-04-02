"""ファイルエクスプローラーUIコンポーネント"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from nicegui import ui

from src.core.backend import RAGBackend


def create_file_explorer(
    backend: RAGBackend,
    on_file_select: Optional[Callable] = None
) -> ui.column:
    """ファイルエクスプローラーを作成する.

    Args:
        backend: RAGBackendインスタンス
        on_file_select: ファイル選択時のコールバック

    Returns:
        ファイルエクスプローラーのコンテナ

    """
    settings = backend.get_user_settings()
    target_dir = settings.get('target_dir', '')
    doc_dir = settings.get('doc_dir', '')

    with ui.column().classes('w-full h-full p-4 gap-4') as container:
        ui.label('ファイルエクスプローラー').classes('text-white text-lg font-bold')

        # ディレクトリ選択
        with ui.row().classes('w-full gap-2'):
            ui.label('ターゲット:').classes('text-gray-400')
            ui.label(target_dir).classes('text-white text-sm')

        with ui.row().classes('w-full gap-2'):
            ui.label('ドキュメント:').classes('text-gray-400')
            ui.label(doc_dir).classes('text-white text-sm')

        # ファイル一覧コンテナ
        file_list_container = ui.column().classes('w-full flex-grow overflow-y-auto')
        _render_file_list(file_list_container, target_dir, doc_dir, on_file_select)

    return container


def _render_file_list(
    container: ui.column,
    target_dir: str,
    doc_dir: str,
    on_file_select: Optional[Callable] = None
) -> None:
    """ファイル一覧を表示する.

    Args:
        container: コンテナ
        target_dir: ターゲットディレクトリ
        doc_dir: ドキュメントディレクトリ
        on_file_select: ファイル選択時のコールバック

    """
    with container:
        # ターゲットディレクトリのファイル
        if target_dir and Path(target_dir).exists():
            ui.label('ターゲットファイル').classes('text-blue-400 font-bold text-sm mt-2')
            _list_files(Path(target_dir), container, on_file_select)

        # ドキュメントディレクトリのファイル
        if doc_dir and Path(doc_dir).exists():
            ui.label('ドキュメントファイル').classes('text-green-400 font-bold text-sm mt-2')
            _list_files(Path(doc_dir), container, on_file_select)


def _list_files(
    directory: Path,
    container: ui.column,
    on_file_select: Optional[Callable] = None
) -> None:
    """ディレクトリ内のファイル一覧を表示.

    Args:
        directory: ディレクトリパス
        container: コンテナ
        on_file_select: ファイル選択時のコールバック

    """
    try:
        files = list(directory.iterdir())
        files.sort(key=lambda x: (x.is_file(), x.name.lower()))

        for item in files[:50]:  # 最大50件まで表示
            if item.is_file():
                with ui.row().classes('w-full items-center gap-2 p-2 hover:bg-gray-700 rounded cursor-pointer'):
                    icon = _get_file_icon(item.suffix)
                    ui.icon(icon).classes('text-gray-400')
                    ui.label(item.name).classes('text-white text-sm flex-1')
                    if on_file_select:
                        ui.button(icon='visibility', on_click=lambda e, p=item: on_file_select(p)).props('flat dense size=sm')
            elif item.is_dir() and not item.name.startswith('.'):
                with ui.row().classes('w-full items-center gap-2 p-2 hover:bg-gray-700 rounded'):
                    ui.icon('folder').classes('text-yellow-400')
                    ui.label(f'{item.name}/').classes('text-gray-300 text-sm')
    except PermissionError:
        ui.label('アクセス権限がありません').classes('text-red-400 text-sm')


def _get_file_icon(suffix: str) -> str:
    """ファイル拡張子に応じたアイコンを返す.

    Args:
        suffix: ファイル拡張子

    Returns:
        アイコン名

    """
    icon_map = {
        '.py': 'code',
        '.js': 'javascript',
        '.ts': 'code',
        '.html': 'html',
        '.css': 'css',
        '.json': 'data_object',
        '.md': 'article',
        '.txt': 'description',
        '.pdf': 'picture_as_pdf',
        '.xlsx': 'table_chart',
        '.pptx': 'slideshow',
    }
    return icon_map.get(suffix.lower(), 'insert_drive_file')