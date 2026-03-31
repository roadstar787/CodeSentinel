# サイドバーUIコンポーネント
from nicegui import ui, app
from rag.base import RAGBackend


def create_sidebar(backend: RAGBackend, on_tab_change=None):
    """サイドバーを作成する"""
    with ui.left_drawer(fixed=True).classes('p-0 bg-[#2d3748]') as drawer:
        # サイドバー内のタブナビゲーション
        with ui.tabs(on_change=on_tab_change).classes('w-full text-slate-500') as tabs:
            tab_exp = ui.tab('EXP', icon='account_tree')  # エクスプローラータブ
            tab_cht = ui.tab('CHATS', icon='chat')  # チャット履歴タブ
            tab_tod = ui.tab('TODOS', icon='check_box')  # ToDoリストタブ
            tab_set = ui.tab('SET', icon='settings')  # 設定タブ
            tab_sts = ui.tab('STS', icon='hub')  # ステータスタブ

        # タブの内容パネル (空の状態で作成し、呼び出し側で中身を追加)
        tab_panels = ui.tab_panels(tabs, value=tab_exp).classes('w-full bg-transparent p-4')

        # アプリケーションをシャットダウンするボタン
        ui.button('SHUTDOWN', on_click=app.shutdown).props('flat icon=power_settings_new color=red-4').classes('w-full mt-auto mb-4 px-4')
        
        return drawer, tabs, tab_exp, tab_cht, tab_tod, tab_set, tab_sts, tab_panels