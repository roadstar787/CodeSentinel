"""サイドバーUIコンポーネント"""

from collections import Counter
from typing import Any, Callable, Dict, List, Optional, Tuple

from nicegui import ui, app

from src.core.backend import RAGBackend
from src.ui.components.sidebar_tabs import (
    create_explorer_tab,
    create_chat_history_tab,
    create_todo_tab,
    create_settings_tab,
    create_status_tab,
)
from src.ui.components.sidebar_tabs.chat_history_tab import (
    _render_chat_list,
    _start_new_chat,
)


# グローバル状態：サイドバーのタブとパネルの参照を保持
_sidebar_state: Dict[str, Any] = {
    'tabs': None,
    'tab_panels': None,
    'tabs_list': [],
}


def set_sidebar_tabs_enabled(enabled: bool) -> None:
    """サイドバーのタブ切り替えを有効化/無効化する.

    Args:
        enabled: 有効化する場合はTrue、無効化する場合はFalse
    """
    tabs = _sidebar_state.get('tabs')
    print(f"[DEBUG] [Tab] Toggle Tabs Interaction: {enabled} (Current Value: {tabs.value if tabs else 'None'})")
    
    if tabs:
        if not enabled:
            # 現在アクティブなタブを永続化（接続断などでリセットされた場合に備える）
            try:
                app.storage.user['active_sidebar_tab'] = tabs.value
            except RuntimeError:
                pass
            # クリック操作を無効化し、見た目を少し薄くする
            tabs.classes(add='pointer-events-none opacity-80 transistion-opacity')
        else:
            # クリック操作を有効化
            tabs.classes(remove='pointer-events-none opacity-80')
            
            # 永続化ストレージから値を復元
            try:
                saved_tab = app.storage.user.get('active_sidebar_tab')
                if saved_tab:
                    print(f"[DEBUG] [Tab] Restoring Active Tab: {saved_tab}")
                    tabs.value = saved_tab
            except RuntimeError:
                pass


def register_sidebar_elements(
    tabs: Any,
    tab_panels: Any,
    tabs_list: List[Any],
) -> None:
    """サイドバーの要素を登録する（タブ無効化用）.

    Args:
        tabs: ui.tabsインスタンス
        tab_panels: ui.tab_panelsインスタンス
        tabs_list: タブのリスト
    """
    _sidebar_state['tabs'] = tabs
    _sidebar_state['tab_panels'] = tab_panels
    _sidebar_state['tabs_list'] = tabs_list


def create_sidebar(
    backend: RAGBackend,
    session: Optional[Dict[str, Any]] = None,
    state: Optional[Dict[str, Any]] = None,
    on_tab_change: Optional[Callable] = None,
    preview_open: Optional[Callable] = None,
    on_tab_toggle: Optional[Callable[[bool], None]] = None,
) -> Tuple:
    """サイドバーを作成する.

    Args:
        backend: RAGBackendインスタンス
        session: チャットセッション
        state: 検索状態
        on_tab_change: タブ変更時のコールバック
        preview_open: プレビュー表示コールバック

    Returns:
        (drawer, tabs, tab_exp, tab_cht, tab_tod, tab_set, tab_sts, tab_panels)

    """

    # 状態管理用
    if session is None:
        session = {'id': '', 'history': []}
    if state is None:
        state = {'hit_counts': Counter()}

    # 共有の統計情報ラベル辞書 (SETタブとSTSタブで共有)
    shared_stats_labels: Dict[str, ui.label] = {}

    # タブ変更時のコールバック（永続化のため）
    def handle_tab_change(e):
        try:
            app.storage.user['active_sidebar_tab'] = e.value
            print(f"[DEBUG] [Tab] User switched to: {e.value}")
        except RuntimeError:
            pass

    with ui.left_drawer(fixed=True).classes('p-0 bg-[#2d3748]') as drawer:
        # 初期表示タブを取得（永続化ストレージから）
        try:
            initial_tab_value = app.storage.user.get('active_sidebar_tab', 'EXP')
        except RuntimeError:
            initial_tab_value = 'EXP'
            
        print(f"[DEBUG] [UI] Creating Sidebar (Initial Tab: {initial_tab_value})")

        # サイドバー内のタブナビゲーション
        with ui.tabs(value=initial_tab_value, on_change=handle_tab_change).classes('w-full text-slate-500') as tabs:
            tab_exp = ui.tab('EXP', icon='account_tree').style('font-size: 11px;')
            tab_cht = ui.tab('CHATS', icon='chat').style('font-size: 11px;')
            tab_tod = ui.tab('TODOS', icon='check_box').style('font-size: 11px;')
            tab_set = ui.tab('SET', icon='settings').style('font-size: 11px;')
            tab_sts = ui.tab('STS', icon='hub').style('font-size: 11px;')

        # タブの内容パネル
        # Note: tabs.value と同期するため、ここでも initial_tab_value を考慮
        tab_panels = ui.tab_panels(tabs, value=initial_tab_value).classes('w-full bg-transparent p-4')

        # EXPタブ
        with tab_panels:
            with ui.tab_panel(tab_exp):
                ui.label('EXPLORER').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
                create_explorer_tab(backend, state, preview_open)

        # CHATSタブ
        with tab_panels:
            with ui.tab_panel(tab_cht):
                create_chat_history_tab(backend, session, state)

        # TODOSタブ
        with tab_panels:
            with ui.tab_panel(tab_tod):
                create_todo_tab(backend)

        # SETタブ
        with tab_panels:
            with ui.tab_panel(tab_set):
                ui.label('CONFIG').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
                create_settings_tab(backend, stats_labels=shared_stats_labels)

        # STSタブ
        with tab_panels:
            with ui.tab_panel(tab_sts).classes('p-6'):
                ui.label('SYSTEM STATUS').classes('text-[10px] font-bold text-indigo-400 mb-4 tracking-widest')
                create_status_tab(backend, stats_labels=shared_stats_labels)

        # シャットダウンボタン
        ui.button('SHUTDOWN', on_click=app.shutdown).props(
            'flat icon=power_settings_new color=red-4'
        ).classes('w-full mt-auto mb-4 px-4')

    # 再構築状態を監視してタブの操作可否を同期する (リロード対策)
    def sync_tabs_interaction():
        is_rebuilding = backend.stats.get('is_rebuilding', False) if backend else False
        if is_rebuilding:
            tabs.classes(add='pointer-events-none opacity-80 transition-opacity')
        else:
            tabs.classes(remove='pointer-events-none opacity-80')
    
    ui.timer(1.0, sync_tabs_interaction)

    # サイドバー要素を登録
    register_sidebar_elements(tabs, tab_panels, [tab_exp, tab_cht, tab_tod, tab_set, tab_sts])

    # 初期化タイマー
    ui.timer(0.5, lambda: None, once=True)

    return drawer, tabs, tab_exp, tab_cht, tab_tod, tab_set, tab_sts, tab_panels