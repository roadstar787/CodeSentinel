"""サイドバーUIコンポーネント"""

from typing import Any, Callable, Dict, Optional, Tuple

from nicegui import ui, app

from src.core.backend import RAGBackend


def create_sidebar(
    backend: RAGBackend,
    on_tab_change: Optional[Callable] = None
) -> Tuple:
    """サイドバーを作成する.

    Args:
        backend: RAGBackendインスタンス
        on_tab_change: タブ変更時のコールバック

    Returns:
        (drawer, tabs, tab_exp, tab_cht, tab_tod, tab_set, tab_sts, tab_panels)

    """
    with ui.left_drawer(fixed=True).classes('p-0 bg-[#2d3748]') as drawer:
        # サイドバー内のタブナビゲーション
        with ui.tabs(on_change=on_tab_change).classes('w-full text-slate-500') as tabs:
            tab_exp = ui.tab('EXP', icon='account_tree')  # エクスプローラータブ
            tab_cht = ui.tab('CHATS', icon='chat')  # チャット履歴タブ
            tab_tod = ui.tab('TODOS', icon='check_box')  # ToDoリストタブ
            tab_set = ui.tab('SET', icon='settings')  # 設定タブ
            tab_sts = ui.tab('STS', icon='hub')  # ステータスタブ

        # タブの内容パネル
        tab_panels = ui.tab_panels(tabs, value=tab_exp).classes('w-full bg-transparent p-4')

        # EXPタブの内容
        with tab_panels:
            with ui.tab_panel(tab_exp):
                ui.label('エクスプローラー').classes('text-white text-lg font-bold')
                ui.label('ファイル一覧をここに表示').classes('text-gray-400')

            with ui.tab_panel(tab_cht):
                ui.label('チャット履歴').classes('text-white text-lg font-bold')
                chat_list_container = ui.column().classes('w-full')
                _render_chat_list(chat_list_container, backend)

            with ui.tab_panel(tab_tod):
                ui.label('ToDoリスト').classes('text-white text-lg font-bold')
                todo_list_container = ui.column().classes('w-full')
                _render_todo_list(todo_list_container, backend)

            with ui.tab_panel(tab_set):
                ui.label('設定').classes('text-white text-lg font-bold')
                _render_settings(backend)

            with ui.tab_panel(tab_sts):
                ui.label('ステータス').classes('text-white text-lg font-bold')
                stats_container = ui.column().classes('w-full')
                _render_stats(stats_container, backend)

        # シャットダウンボタン
        ui.button('SHUTDOWN', on_click=app.shutdown).props('flat icon=power_settings_new color=red-4').classes('w-full mt-auto mb-4 px-4')

    return drawer, tabs, tab_exp, tab_cht, tab_tod, tab_set, tab_sts, tab_panels


def _render_chat_list(container: ui.column, backend: RAGBackend) -> None:
    """チャット一覧を表示."""
    with container:
        chats = backend.list_chats()
        if not chats:
            ui.label('チャット履歴がありません').classes('text-gray-400')
        else:
            for chat in chats[:10]:  # 最新10件まで表示
                with ui.row().classes('w-full items-center cursor-pointer hover:bg-gray-700 p-2 rounded'):
                    ui.icon('chat', size='sm').classes('text-blue-400')
                    ui.label(chat.get('title', 'Untitled')).classes('text-white flex-1')
                    ui.label(chat.get('date', '')[:10]).classes('text-gray-400 text-xs')


def _render_todo_list(container: ui.column, backend: RAGBackend) -> None:
    """ToDoリストを表示."""
    with container:
        todos = backend.get_todo_service().list_todos(show_completed=False)
        if not todos:
            ui.label('ToDoがありません').classes('text-gray-400')
        else:
            for todo in todos[:10]:  # 最新10件まで表示
                with ui.row().classes('w-full items-center p-2 rounded'):
                    ui.checkbox(value=todo.get('completed', False), on_change=lambda: None).classes('text-green-400')
                    ui.label(todo.get('title', '')).classes('text-white flex-1')
                    priority_color = {'high': 'red', 'medium': 'yellow', 'low': 'green'}.get(todo.get('priority', 'medium'), 'gray')
                    ui.icon('circle', color=priority_color, size='xs')


def _render_settings(backend: RAGBackend) -> None:
    """設定を表示."""
    settings = backend.get_user_settings()
    with ui.column().classes('w-full gap-4'):
        ui.input('ターゲットディレクトリ', value=str(settings.get('target_dir', ''))).classes('w-full')
        ui.input('ドキュメントディレクトリ', value=str(settings.get('doc_dir', ''))).classes('w-full')
        mode_options = ['Normal', 'Gap']
        ui.select(mode_options, value=settings.get('mode', 'Normal'), label='モード').classes('w-full')
        ui.button('保存', on_click=lambda: ui.notify('設定を保存しました')).props('color=blue-500')


def _render_stats(container: ui.column, backend: RAGBackend) -> None:
    """統計情報を表示."""
    stats = backend.get_document_service().get_statistics()
    with container:
        ui.label(f'総チャンク数: {stats.get("total_chunks", 0)}').classes('text-white')
        ui.label(f'ベクトルストア: {"ロード済み" if stats.get("vector_store_loaded", False) else "未ロード"}').classes('text-white')
        ui.label(f'LM Studio: {"接続済み" if stats.get("lm_connected", False) else "未接続"}').classes('text-white')
        ui.button('データベース再構築', on_click=lambda: ui.notify('再構築を開始しました')).props('color=orange-500')