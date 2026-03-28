# メインページを定義します。NiceGUIのルート ('/') に関連付けられます。
import uuid
from datetime import datetime
from pathlib import Path

from nicegui import ui, app
from rag.base import RAGBackend
from config import settings


async def main_page(backend: RAGBackend):
    # ユーザー設定からターゲットディレクトリをロード。設定がなければRAGBackendのデフォルトを使用。
    user_settings = backend.get_user_settings()
    backend.update_user_settings(app.storage.user.get('user_settings', user_settings))
    
    # チャットセッション管理
    session = {'id': app.storage.user.get('current_chat_id', str(uuid.uuid4())), 'history': []}
    chat_data = backend.load_chat(session['id'])
    if chat_data: session['history'] = chat_data.get('messages', [])

    # 検索状態の管理（ヒット数など）
    state = {'hit_counts': {}}

    return session, state
