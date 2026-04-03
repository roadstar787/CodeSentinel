"""メインページを定義します。NiceGUIのルート ('/') に関連付けられます。"""

import uuid
from typing import Any, Dict, Tuple

from nicegui import ui, app

from src.core.backend import RAGBackend
from src.ui.components.sidebar import create_sidebar
from src.ui.components.chat_interface import create_chat_interface
from src.ui.components.header import create_header
from src.ui.components.preview_dialog import create_preview_dialog
from src.ui.components.status_updater import create_status_updater


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
    # セッションと状態を初期化
    session = {
        'id': str(uuid.uuid4()),
        'history': []
    }
    state: Dict[str, Any] = {'hit_counts': {}}

    # プレビューダイアログの作成
    get_preview_dialog, open_preview = create_preview_dialog()

    # ヘッダーの作成
    mode_toggle = create_header(
        app_name="CodeSentinel",
        version="0.4.0",
        on_toggle_mode=lambda e: backend.update_user_settings({'mode': e.value})
    )

    # サイドバーの作成
    drawer, tabs, tab_exp, tab_cht, tab_tod, tab_set, tab_sts, tab_panels = create_sidebar(backend)

    # メインコンテンツエリア
    with ui.column().classes('w-full h-full p-4 gap-4'):
        # チャットインターフェース
        create_chat_interface(backend, session, state)

    # データベースの初期ロード
    backend.load_db()

    # ステータス更新ループの開始（STSタブ）
    def setup_status_tab():
        """ステータスタブのUI要素を設定する."""
        with ui.column().classes('w-full gap-2'):
            cpu_label = ui.label('0%').classes('text-white')
            ram_label = ui.label('0GB').classes('text-white')
            lm_status_chip = ui.label('OFFLINE').classes('text-white')
            lm_model_label = ui.label('N/A').classes('text-white')
            status_chip = ui.label('OFFLINE').classes('text-white')
            chunk_count_label = ui.label('0').classes('text-white')
            last_update_label = ui.label('Never').classes('text-white')

            # ステータス更新ループを開始
            start_status_loop = create_status_updater()
            start_status_loop(
                cpu_label, ram_label, lm_status_chip, lm_model_label,
                status_chip, chunk_count_label, last_update_label, backend
            )

    # タイマーでステータス更新を設定
    ui.timer(1.0, lambda: None, once=True)  # 初期化後に実行

    # モード切替ハンドラ
    def on_mode_change(e):
        """モード切替時のハンドラ."""
        backend.update_user_settings({'mode': e.value})

    if mode_toggle:
        ui.timer(0.1, lambda: mode_toggle.on('change', on_mode_change), once=True)