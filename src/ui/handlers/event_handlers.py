"""UIイベントハンドラ"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from nicegui import ui

from src.core.backend import RAGBackend


class EventHandlers:
    """UIのイベントハンドラを管理するクラス."""

    def __init__(
        self,
        backend: RAGBackend,
        preview_open_func: Callable,
        refresh_explorer_func: Callable
    ) -> None:
        """初期化.

        Args:
            backend: RAGBackendインスタンス
            preview_open_func: プレビューダイアログを開く関数
            refresh_explorer_func: ファイルエクスプローラーを更新する関数

        """
        self.backend = backend
        self.preview_open = preview_open_func
        self.refresh_explorer_func = refresh_explorer_func
        self.chat_service = backend.get_chat_service()
        self.todo_service = backend.get_todo_service()

    def change_mode(self, value: str) -> None:
        """モードを変更する.

        Args:
            value: モード値（'Normal' または 'Gap'）

        """
        self.backend.mode = value
        self.backend.update_user_settings({'mode': value})

    def save_settings(self, path_input: Any, doc_path_input: Any) -> None:
        """設定を保存する.

        Args:
            path_input: ターゲットディレクトリ入力フィールド
            doc_path_input: ドキュメントディレクトリ入力フィールド

        """
        user_settings = {
            'target_dir': path_input,
            'doc_dir': doc_path_input,
            'mode': self.backend.mode
        }
        self.backend.update_user_settings(user_settings)
        self.refresh_explorer_func()
        ui.notify('設定を保存しました', color='positive')

    async def rebuild_task(self, refresh_explorer_func: Callable) -> tuple[bool, str]:
        """再構築タスクを実行する.

        Args:
            refresh_explorer_func: ファイルエクスプローラーを更新する関数

        Returns:
            (成功フラグ, メッセージ)

        """
        success, msg = await self.backend.rebuild_db()

        if success:
            ui.notify('Rebuild successful!', color='positive')
            refresh_explorer_func()
        else:
            ui.notify(f'Rebuild failed: {msg}', color='negative')

        return success, msg

    def refresh_chat_list(
        self,
        session: Dict[str, Any],
        chat_results: Any,
        chat_list_container: Any
    ) -> None:
        """チャットリストを更新する.

        Args:
            session: チャットセッション
            chat_results: チャット結果コンテナ
            chat_list_container: チャットリストコンテナ

        """
        chat_list_container.clear()
        chats = self.backend.list_chats()
        if not chats:
            ui.label('No history').classes('text-[10px] text-slate-500 italic p-2')
        for c in chats:
            with ui.row().classes('w-full items-center gap-1 group'):
                is_current = (c['id'] == session.get('id'))
                bg_class = 'bg-slate-700/80 border-l-2 border-indigo-500' if is_current else 'hover:bg-slate-700/50'

                chat_id = c['id']
                ui.button(
                    on_click=lambda e, cid=chat_id: self.load_chat_session(session, cid, chat_results, chat_list_container)
                ).props(f'flat no-caps dense {bg_class}').classes('flex-grow text-left justify-start px-2 py-1 rounded')

    def load_chat_session(
        self,
        session: Dict[str, Any],
        chat_id: str,
        chat_results: Any,
        chat_list_container: Any
    ) -> None:
        """チャットセッションをロードする.

        Args:
            session: チャットセッション
            chat_id: チャットID
            chat_results: チャット結果コンテナ
            chat_list_container: チャットリストコンテナ

        """
        data = self.backend.load_chat(chat_id)
        if not data:
            return

        session['id'] = chat_id
        session['history'] = data.get('messages', [])

        chat_results.clear()
        with chat_results:
            for msg in session['history']:
                if msg['role'] == 'user':
                    ui.label(f"Q: {msg['content']}").classes('text-indigo-600 font-bold text-sm bg-indigo-50 p-2 w-full border-l-4 border-indigo-600')
                else:
                    ui.markdown(msg['content']).classes('text-slate-700 text-sm p-4 w-full border-b')
                    with ui.row().classes('w-full justify-end items-center mb-4'):
                        ui.button(
                            'COPY MARKDOWN',
                            icon='content_copy',
                            on_click=lambda f=msg['content']: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(f)})')
                        ).props('flat dense color=slate-400 size=sm').classes('opacity-50 hover:opacity-100')

                    if msg.get('sources'):
                        with ui.row().classes('gap-2 mt-[-10px] mb-4 ml-4'):
                            for p, t in msg['sources']:
                                b_dir = self.backend.config.paths.get_target_dir() if t == 'code' else self.backend.config.paths.get_doc_dir()
                                ui.button(
                                    f"📄 {p}",
                                    on_click=lambda fp=p, bd=str(b_dir): self.preview_open(fp, bd)
                                ).props('flat dense size=sm color=indigo-400 font-bold').classes('text-[10px] bg-indigo-50/50 px-2 rounded border border-indigo-100/50 hover:bg-indigo-100 transition-colors')

        ui.notify(f"Chat loaded: {data.get('title', '')}")
        self.refresh_chat_list(session, chat_results, chat_list_container)

    def start_new_chat(
        self,
        session: Dict[str, Any],
        chat_results: Any,
        chat_list_container: Any
    ) -> None:
        """新しいチャットを開始する.

        Args:
            session: チャットセッション
            chat_results: チャット結果コンテナ
            chat_list_container: チャットリストコンテナ

        """
        session['id'] = str(uuid.uuid4())
        session['history'] = []
        chat_results.clear()
        ui.notify("New chat session started")
        self.refresh_chat_list(session, chat_results, chat_list_container)

    def delete_chat_session(
        self,
        chat_id: str,
        session: Dict[str, Any],
        chat_results: Any,
        chat_list_container: Any
    ) -> None:
        """チャットセッションを削除する.

        Args:
            chat_id: チャットID
            session: チャットセッション
            chat_results: チャット結果コンテナ
            chat_list_container: チャットリストコンテナ

        """
        self.backend.delete_chat(chat_id)
        ui.notify("Chat deleted")
        if session.get('id') == chat_id:
            self.start_new_chat(session, chat_results, chat_list_container)
        else:
            self.refresh_chat_list(session, chat_results, chat_list_container)