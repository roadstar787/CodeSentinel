"""メインページを定義します。NiceGUIのルート ('/') に関連付けられます。"""

import uuid
from typing import Any, Dict, Optional, Tuple

from nicegui import ui, app

from src.core.backend import RAGBackend
from src.ui.components.sidebar import create_sidebar
from src.ui.components.chat_interface import create_chat_interface
from src.ui.components.header import create_header
from src.ui.components.preview_dialog import create_preview_dialog


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
    print(f"[DEBUG] [UI] Initializing Main UI (Client ID: {id(backend)})")
    # ユーザー設定を永続化ストレージから復元（なければデフォルト）
    try:
        saved_settings = app.storage.user.get('user_settings', {})
        if saved_settings:
            backend.update_user_settings(saved_settings)
        else:
            # デフォルト設定をstorageに保存
            default_settings = backend.get_user_settings()
            app.storage.user['user_settings'] = default_settings
    except RuntimeError:
        # テスト環境などstorageが使用できない場合はデフォルト設定を使用
        pass

    # データベースの初期ロード（設定更新後に行う）
    db_loaded = backend.load_db()
    if not db_loaded:
        try:
            ui.notify('データベースが見つかりません。設定からデータベース再構築を実行してください。', color='warning', timeout=10000)
        except RuntimeError:
            pass

    # チャットセッション管理（永続化）
    try:
        saved_chat_id = app.storage.user.get('current_chat_id')
    except RuntimeError:
        saved_chat_id = None

    session: Dict[str, Any] = {
        'id': saved_chat_id or str(uuid.uuid4()),
        'history': []
    }
    # 保存されたチャット履歴を復元
    if saved_chat_id:
        chat_data = backend.load_chat(saved_chat_id)
        if chat_data:
            session['history'] = chat_data.get('messages', [])

    state: Dict[str, Any] = {'hit_counts': {}}

    # プレビューダイアログの作成
    get_preview_dialog, open_preview = create_preview_dialog()

    # チャットインターフェースの作成（コンテナを取得）
    chat_container = create_chat_interface(backend, session, state, preview_open=open_preview)
    # チャットメッセージ表示エリア（最初の子要素）を取得
    chat_results = None
    if hasattr(chat_container, 'default_slot') and chat_container.default_slot:
        children = getattr(chat_container.default_slot, 'children', [])
        if children:
            chat_results = children[0]

    # タブ切り替えコールバック（再構築中にタブ切り替えを無効化するため）
    def on_tab_toggle(enabled: bool) -> None:
        """タブの切り替えを有効化/無効化する."""
        from src.ui.components.sidebar import set_sidebar_tabs_enabled
        set_sidebar_tabs_enabled(enabled)

    # サイドバーの作成（session, state, preview_open, chat_resultsを渡す）
    drawer, tabs, tab_exp, tab_cht, tab_tod, tab_set, tab_sts, tab_panels = create_sidebar(
        backend,
        session=session,
        state=state,
        preview_open=open_preview,
        chat_results=chat_results,
        on_tab_toggle=on_tab_toggle,
    )

    # モード切り替えコールバック
    def on_toggle_mode(e: Any) -> None:
        backend.mode = e.value
        try:
            app.storage.user['mode'] = e.value
        except RuntimeError:
            pass
        ui.notify(f"モードを{e.value}に変更しました", color='info')

    # ヘッダーの作成（drawerを渡す）
    create_header(
        app_name="CodeSentinel",
        version="0.4.0",
        drawer=drawer,
        on_toggle_mode=on_toggle_mode,
    )

    # 初期化タイマー
    ui.timer(0.5, lambda: None, once=True)