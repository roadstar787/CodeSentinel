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
                from src.ui.components.file_explorer import create_file_explorer
                create_file_explorer(backend)

            with ui.tab_panel(tab_cht):
                ui.label('チャット履歴').classes('text-white text-lg font-bold')
                chat_list_container = ui.column().classes('w-full')
                _render_chat_list(chat_list_container, backend)

            with ui.tab_panel(tab_tod):
                from src.ui.components.todo_manager import create_todo_manager
                create_todo_manager(backend)

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
        # バインディング用コンテナ
        container = {'target_dir': str(settings.get('target_dir', '')),
                     'doc_dir': str(settings.get('doc_dir', '')),
                     'mode': str(settings.get('mode', 'Normal'))}
        
        def save_settings():
            new_settings = {
                'target_dir': container['target_dir'],
                'doc_dir': container['doc_dir'],
                'mode': container['mode']
            }
            backend.update_user_settings(new_settings)
            ui.notify('設定を保存しました')
        
        ui.label('ターゲットディレクトリ').classes('text-white')
        target_input = ui.input(value=container['target_dir']).classes('w-full')
        target_input.on('blur', lambda _: container.update(target_dir=target_input.value))
        
        ui.label('ドキュメントディレクトリ').classes('text-white')
        doc_input = ui.input(value=container['doc_dir']).classes('w-full')
        doc_input.on('blur', lambda _: container.update(doc_dir=doc_input.value))
        
        mode_options = ['Normal', 'Gap']
        ui.label('モード').classes('text-white')
        mode_select = ui.select(mode_options, value=container['mode']).classes('w-full')
        mode_select.on('blur', lambda _: container.update(mode=mode_select.value))
        
        ui.button('保存', on_click=save_settings).props('color=blue-500')


def _render_stats(container: ui.column, backend: RAGBackend) -> None:
    """統計情報を表示."""
    async def rebuild_database():
        ui.notify('データベース再構築を開始します...')
        try:
            success, message = await backend.rebuild_db()
            if success:
                ui.notify(message)
                # 統計情報を更新
                container.clear()
                _render_stats(container, backend)
            else:
                ui.notify(f'再構築に失敗しました: {message}', color='red')
        except Exception as e:
            ui.notify(f'エラーが発生しました: {str(e)}', color='red')
    
    stats = backend.get_document_service().get_statistics()
    with container:
        ui.label(f'総チャンク数: {stats.get("total_chunks", 0)}').classes('text-white')
        ui.label(f'ベクトルストア: {"ロード済み" if stats.get("vector_store_loaded", False) else "未ロード"}').classes('text-white')
        ui.label(f'LM Studio: {"接続済み" if stats.get("lm_connected", False) else "未接続"}').classes('text-white')
        ui.button('データベース再構築', on_click=rebuild_database).props('color=orange-500')
