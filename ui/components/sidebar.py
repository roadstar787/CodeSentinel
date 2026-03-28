# サイドバーUIコンポーネント
from nicegui import ui
from rag.base import RAGBackend


def create_sidebar(backend: RAGBackend, on_tab_change):
    """サイドバーを作成する"""
    with ui.left_drawer(fixed=True).classes('p-0 bg-[#2d3748]') as drawer:
        # サイドバー内のタブナビゲーション
        with ui.tabs().classes('w-full text-slate-500') as tabs:
            tab_exp = ui.tab('EXP', icon='account_tree')  # エクスプローラータブ
            tab_cht = ui.tab('CHATS', icon='chat')  # チャット履歴タブ
            tab_tod = ui.tab('TODOS', icon='check_box')  # ToDoリストタブ
            tab_set = ui.tab('SET', icon='settings')  # 設定タブ
            tab_sts = ui.tab('STS', icon='hub')  # ステータスタブ

        # タブの内容パネル
        with ui.tab_panels(tabs, value=tab_exp).classes('w-full bg-transparent p-4'):
            # 各タブのコンテンツは呼び出し側で設定
            pass

        # アプリケーションをシャットダウンするボタン
        ui.button('SHUTDOWN', on_click=lambda: ui.run_javascript('window.location.reload()')).props('flat icon=power_settings_new color=red-4').classes('w-full mt-auto mb-4 px-4')
        
        return drawer, tabs