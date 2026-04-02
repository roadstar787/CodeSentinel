"""メインページを定義します。NiceGUIのルート ('/') に関連付けられます。"""

import uuid
from typing import Any, Dict, Tuple

from nicegui import ui, app

from src.core.backend import RAGBackend
from src.ui.components.sidebar import create_sidebar


async def main_page(backend: RAGBackend) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """メインページを作成する.

    Args:
        backend: RAGBackendインスタンス

    Returns:
        (session, state)

    """
    # ユーザー設定からターゲットディレクトリをロード
    user_settings = backend.get_user_settings()
    backend.update_user_settings(app.storage.user.get('user_settings', user_settings))

    # チャットセッション管理
    session = {
        'id': app.storage.user.get('current_chat_id', str(uuid.uuid4())),
        'history': []
    }
    chat_data = backend.load_chat(session['id'])
    if chat_data:
        session['history'] = chat_data.get('messages', [])

    # 検索状態の管理
    state: Dict[str, Any] = {'hit_counts': {}}

    return session, state


def create_main_ui(backend: RAGBackend) -> None:
    """メインUIを作成する.

    Args:
        backend: RAGBackendインスタンス

    """
    # サイドバーを先に作成
    drawer, tabs, tab_exp, tab_cht, tab_tod, tab_set, tab_sts, tab_panels = create_sidebar(backend)

    # ヘッダー
    with ui.header().classes('bg-[#1a202c] text-white items-center'):
        ui.label('CodeSentinel v2.0').classes('text-xl font-bold')
        ui.space()
        with ui.button(icon='menu', on_click=lambda: drawer.toggle()).props('flat dense'):
            pass

    # メインコンテンツエリア
    with ui.column().classes('w-full h-full p-4'):
        ui.label('メインコンテンツ').classes('text-2xl font-bold')
        ui.label('ここにチャットインターフェースなどを配置').classes('text-gray-500')
