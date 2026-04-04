"""サイドバーUIコンポーネント"""

import asyncio
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from nicegui import ui, app

from src.core.backend import RAGBackend

# チャットメッセージ表示エリアへの参照（グローバル）
_chat_results_ref: Dict[str, Any] = {'container': None}


def create_sidebar(
    backend: RAGBackend,
    session: Optional[Dict[str, Any]] = None,
    state: Optional[Dict[str, Any]] = None,
    on_tab_change: Optional[Callable] = None,
    preview_open: Optional[Callable] = None,
    chat_results: Optional[ui.column] = None,
) -> Tuple:
    """サイドバーを作成する.

    Args:
        backend: RAGBackendインスタンス
        session: チャットセッション
        state: 検索状態
        on_tab_change: タブ変更時のコールバック
        preview_open: プレビュー表示コールバック
        chat_results: チャットメッセージ表示エリア

    Returns:
        (drawer, tabs, tab_exp, tab_cht, tab_tod, tab_set, tab_sts, tab_panels)

    """
    # チャット結果コンテナを保存
    if chat_results is not None:
        _chat_results_ref['container'] = chat_results

    # 状態管理用
    if session is None:
        session = {'id': '', 'history': []}
    if state is None:
        state = {'hit_counts': Counter()}

    # UIコンテナ参照
    tree_container = None
    chat_list_container = None
    todo_list_container = None
    todo_stats_container = None
    stats_labels: Dict[str, ui.label] = {}

    with ui.left_drawer(fixed=True).classes('p-0 bg-[#2d3748]') as drawer:
        # サイドバー内のタブナビゲーション
        with ui.tabs().classes('w-full text-slate-500') as tabs:
            tab_exp = ui.tab('EXP', icon='account_tree')
            tab_cht = ui.tab('CHATS', icon='chat')
            tab_tod = ui.tab('TODOS', icon='check_box')
            tab_set = ui.tab('SET', icon='settings')
            tab_sts = ui.tab('STS', icon='hub')

        # タブの内容パネル
        tab_panels = ui.tab_panels(tabs, value=tab_exp).classes('w-full bg-transparent p-4')

        # EXPタブ
        with tab_panels:
            with ui.tab_panel(tab_exp):
                ui.label('EXPLORER').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
                tree_container = ui.column().classes('w-full gap-0')

        # CHATSタブ
        with tab_panels:
            with ui.tab_panel(tab_cht):
                with ui.row().classes('w-full items-center justify-between mb-4'):
                    ui.label('HISTORY').classes('text-[10px] text-slate-600 tracking-widest')
                    ui.button(
                        icon='add',
                        on_click=lambda: _start_new_chat(session, chat_list_container)
                    ).props('flat round dense color=slate-400')
                chat_list_container = ui.column().classes('w-full gap-2')

        # TODOSタブ
        with tab_panels:
            with ui.tab_panel(tab_tod):
                with ui.row().classes('w-full items-center justify-between mb-4'):
                    ui.label('TODOS').classes('text-[10px] text-slate-600 tracking-widest')
                    ui.button(
                        icon='add',
                        on_click=lambda: _show_add_todo_dialog(backend, todo_list_container, todo_stats_container)
                    ).props('flat round dense color=slate-400')
                todo_stats_container = ui.row().classes('w-full gap-4 mb-4')
                todo_list_container = ui.column().classes('w-full gap-2')

        # SETタブ
        with tab_panels:
            with ui.tab_panel(tab_set):
                ui.label('CONFIG').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
                _render_settings(backend, stats_labels)

        # STSタブ
        with tab_panels:
            with ui.tab_panel(tab_sts).classes('p-6'):
                ui.label('SYSTEM STATUS').classes('text-[10px] font-bold text-indigo-400 mb-4 tracking-widest')
                stats_container = ui.column().classes('w-full')
                stats_labels = _render_stats(stats_container, backend)

        # シャットダウンボタン
        ui.button('SHUTDOWN', on_click=app.shutdown).props('flat icon=power_settings_new color=red-4').classes('w-full mt-auto mb-4 px-4')

    # 初期化処理
    def init_sidebar():
        """サイドバーを初期化."""
        _refresh_explorer(tree_container, backend, state, preview_open)
        _render_chat_list(chat_list_container, backend, session)
        _refresh_todo_list(todo_list_container, todo_stats_container, backend)

    # 初期化タイマー
    ui.timer(0.5, init_sidebar, once=True)

    return drawer, tabs, tab_exp, tab_cht, tab_tod, tab_set, tab_sts, tab_panels


def _refresh_explorer(
    tree_container: ui.column,
    backend: RAGBackend,
    state: Dict[str, Any],
    preview_open: Optional[Callable] = None,
) -> None:
    """エクスプローラーを更新."""
    if tree_container is None:
        return

    try:
        tree_container.clear()
    except RuntimeError:
        return
    except Exception:
        pass

    def build_nodes(path: Path, relative_to: Path, supported_exts: set) -> dict:
        """ツリーノードを構築."""
        rel = str(path.relative_to(relative_to)) if path != relative_to else ""
        hits = state.get('hit_counts', Counter()).get(rel, 0)
        hit_label = f" • {hits}" if hits > 0 else ""
        bg_style = f"background: rgba(99, 102, 241, {min(hits * 0.15, 0.4)});" if hits > 0 else ""

        node = {
            "id": rel if path.is_file() else None,
            "label": path.name + hit_label,
            "class": "hit-file" if hits > 0 else "",
            "style": bg_style
        }
        if path.is_dir():
            children = []
            try:
                for p in sorted(path.iterdir()):
                    if p.name.startswith('.'):
                        continue
                    if p.is_dir():
                        child_node = build_nodes(p, relative_to, supported_exts)
                        if child_node["children"] or child_node["id"]:
                            children.append(child_node)
                    elif p.suffix.lower() in supported_exts:
                        children.append(build_nodes(p, relative_to, supported_exts))
            except PermissionError:
                pass

            node["children"] = children
            node["icon"] = "folder"
        else:
            ext = path.suffix.lower()
            if ext == ".pdf":
                node["icon"] = "picture_as_pdf"
            elif ext in {".xlsx", ".xls"}:
                node["icon"] = "table_view"
            elif ext == ".pptx":
                node["icon"] = "present_to_all"
            elif ext == ".md":
                node["icon"] = "article"
            else:
                node["icon"] = "description"
        return node

    try:
        CODE_EXTS = {".py", ".cs", ".cpp", ".h", ".hpp", ".json"}
        DOCS_EXTS = {".pdf", ".md", ".xlsx", ".pptx"}

        settings = backend.get_user_settings()
        target_dir = Path(settings.get('target_dir', ''))
        doc_dir_str = settings.get('doc_dir', '')

        # Code Directory
        if target_dir.exists():
            tree_data = [build_nodes(target_dir, target_dir, CODE_EXTS)]
            if tree_data[0]["children"] or tree_data[0]["id"]:
                with tree_container:
                    ui.label('CODE').classes('text-[9px] text-slate-500 mt-2 uppercase tracking-tighter')
                    t = ui.tree(
                        nodes=tree_data,
                        label_key='label',
                        on_select=lambda e: preview_open(e.value, str(target_dir)) if preview_open else None
                    ).props('dark dense expand-all')
                    t.add_slot(
                        'default-header',
                        '<div :class="props.node.class" :style="props.node.style" style="border-radius: 4px; padding: 2px 6px;">{{ props.node.label }}</div>'
                    )

        # Document Directory
        if doc_dir_str:
            doc_dir = Path(doc_dir_str)
            if doc_dir.exists():
                doc_tree_data = [build_nodes(doc_dir, doc_dir, DOCS_EXTS)]
                if doc_tree_data[0]["children"] or doc_tree_data[0]["id"]:
                    with tree_container:
                        ui.label('DOCS').classes('text-[9px] text-slate-500 mt-2 uppercase tracking-tighter')
                        t_doc = ui.tree(
                            nodes=doc_tree_data,
                            label_key='label',
                            on_select=lambda e: preview_open(e.value, str(doc_dir)) if preview_open else None
                        ).props('dark dense expand-all')
                        t_doc.add_slot(
                            'default-header',
                            '<div :class="props.node.class" :style="props.node.style" style="border-radius: 4px; padding: 2px 6px;">{{ props.node.label }}</div>'
                        )
    except Exception as e:
        print(f"Explorer Refresh Error: {e}")


def _render_chat_list(
    container: Optional[ui.column],
    backend: RAGBackend,
    session: Optional[Dict[str, Any]] = None,
) -> None:
    """チャット一覧を表示."""
    if container is None:
        return

    container.clear()
    with container:
        chats = backend.list_chats()
        if not chats:
            ui.label('チャット履歴がありません').classes('text-gray-400')
        else:
            for chat in chats[:10]:
                chat_id = chat.get('id', '')
                with ui.row().classes('w-full items-center cursor-pointer hover:bg-gray-700 p-2 rounded'):
                    ui.icon('chat', size='sm').classes('text-blue-400')
                    # チャットタイトルをクリックしてロード
                    ui.label(chat.get('title', 'Untitled')).classes('text-white flex-1 cursor-pointer').on('click', lambda e, cid=chat_id: _load_chat(cid, backend, session, container))
                    ui.label(chat.get('date', '')[:10]).classes('text-gray-400 text-xs')

                    # 削除ボタン
                    ui.button(
                        icon='delete',
                        on_click=lambda e, cid=chat_id: _delete_chat(cid, backend, session, container)
                    ).props('flat dense size=sm color=red-4').classes('opacity-50 hover:opacity-100')


def _load_chat(
    chat_id: str,
    backend: RAGBackend,
    session: Optional[Dict],
    container: ui.column,
) -> None:
    """チャットをロード."""
    chat_data = backend.load_chat(chat_id)
    if chat_data and session:
        session['id'] = chat_id
        session['history'] = chat_data.get('messages', [])
        ui.notify(f'チャット "{chat_data.get("title", "Untitled")}" をロードしました')
        # 永続化ストレージに保存
        try:
            app.storage.user['current_chat_id'] = chat_id
        except RuntimeError:
            pass
        # チャットインターフェースを更新
        chat_results = _chat_results_ref.get('container')
        if chat_results is not None:
            chat_results.clear()
            from src.ui.components.chat_interface import _render_chat_history
            _render_chat_history(chat_results, session['history'])
    _render_chat_list(container, backend, session)


def _delete_chat(
    chat_id: str,
    backend: RAGBackend,
    session: Optional[Dict],
    container: ui.column,
) -> None:
    """チャットを削除."""
    backend.delete_chat(chat_id)
    ui.notify('チャットを削除しました')
    if session and session.get('id') == chat_id:
        import uuid
        session['id'] = str(uuid.uuid4())
        session['history'] = []
    _render_chat_list(container, backend, session)


def _start_new_chat(
    session: Dict[str, Any],
    chat_list_container: Optional[ui.column] = None,
) -> None:
    """新しいチャットを開始."""
    import uuid
    session['id'] = str(uuid.uuid4())
    session['history'] = []
    ui.notify('新しいチャットを開始しました')
    # チャットインターフェースもクリア
    chat_results = _chat_results_ref.get('container')
    if chat_results is not None:
        chat_results.clear()
    _render_chat_list(chat_list_container, backend=None, session=session)


def _show_add_todo_dialog(
    backend: RAGBackend,
    todo_list_container: Optional[ui.column] = None,
    todo_stats_container: Optional[ui.row] = None,
) -> None:
    """ToDo追加ダイアログを表示."""
    with ui.dialog() as dialog, ui.card():
        ui.label('新しいToDo').classes('text-lg font-bold')
        title_input = ui.input('タイトル').props('outlined')
        priority_select = ui.select(
            options={'high': '高', 'medium': '中', 'low': '低'},
            value='medium',
            label='優先度'
        ).props('outlined')
        with ui.row():
            ui.button('追加', on_click=lambda: _add_todo(backend, title_input.value, priority_select.value, dialog, todo_list_container, todo_stats_container))
            ui.button('キャンセル', on_click=dialog.close)
    dialog.open()


def _add_todo(
    backend: RAGBackend,
    title: str,
    priority: str,
    dialog: ui.dialog,
    todo_list_container: Optional[ui.column] = None,
    todo_stats_container: Optional[ui.row] = None,
) -> None:
    """ToDoを追加."""
    if not title:
        ui.notify('タイトルを入力してください', color='warning')
        return

    backend.get_todo_service().add_todo(title=title, priority=priority)
    ui.notify('ToDoを追加しました')
    dialog.close()
    _refresh_todo_list(todo_list_container, todo_stats_container, backend)


def _refresh_todo_list(
    todo_list_container: Optional[ui.column],
    todo_stats_container: Optional[ui.row],
    backend: RAGBackend,
) -> None:
    """ToDoリストを更新."""
    if todo_list_container is None:
        return

    todo_list_container.clear()
    if todo_stats_container:
        todo_stats_container.clear()

    todo_service = backend.get_todo_service()
    todos = todo_service.list_todos(show_completed=False)

    # 統計情報を表示
    if todo_stats_container:
        stats = todo_service.get_todo_statistics()
        with todo_stats_container:
            ui.label(f'未完了: {stats.get("pending", 0)}').classes('text-yellow-400 text-xs')
            ui.label(f'完了: {stats.get("completed", 0)}').classes('text-green-400 text-xs')

    with todo_list_container:
        if not todos:
            ui.label('ToDoがありません').classes('text-gray-400')
        else:
            for todo in todos[:20]:
                todo_id = todo.get('id', '')
                with ui.row().classes('w-full items-center p-2 rounded hover:bg-gray-700'):
                    cb = ui.checkbox(
                        value=todo.get('completed', False),
                        on_change=lambda checked, tid=todo_id: _toggle_todo(tid, checked.value, backend, todo_list_container, todo_stats_container)
                    ).classes('text-green-400')
                    ui.label(todo.get('title', '')).classes('text-white flex-1 text-sm')
                    priority_color = {'high': 'red', 'medium': 'yellow', 'low': 'green'}.get(todo.get('priority', 'medium'), 'gray')
                    ui.icon('circle', color=priority_color, size='xs')
                    ui.button(
                        icon='delete',
                        on_click=lambda e, tid=todo_id: _delete_todo(tid, backend, todo_list_container, todo_stats_container)
                    ).props('flat dense size=sm color=red-4').classes('opacity-50 hover:opacity-100')


def _toggle_todo(
    todo_id: str,
    completed: bool,
    backend: RAGBackend,
    todo_list_container: Optional[ui.column],
    todo_stats_container: Optional[ui.row],
) -> None:
    """ToDoの完了状態を切り替え."""
    todo_service = backend.get_todo_service()
    todo_service.toggle_todo_completion(todo_id)
    _refresh_todo_list(todo_list_container, todo_stats_container, backend)


def _delete_todo(
    todo_id: str,
    backend: RAGBackend,
    todo_list_container: Optional[ui.column],
    todo_stats_container: Optional[ui.row],
) -> None:
    """ToDoを削除."""
    backend.get_todo_service().delete_todo(todo_id)
    ui.notify('ToDoを削除しました')
    _refresh_todo_list(todo_list_container, todo_stats_container, backend)


def _render_settings(
    backend: RAGBackend,
    stats_labels: Optional[Dict[str, ui.label]] = None,
) -> None:
    """設定を表示."""
    settings = backend.get_user_settings()

    with ui.column().classes('w-full gap-4'):
        ui.label('ターゲットディレクトリ').classes('text-white')
        target_input = ui.input(value=str(settings.get('target_dir', ''))).classes('w-full')

        ui.label('ドキュメントディレクトリ').classes('text-white')
        doc_input = ui.input(value=str(settings.get('doc_dir', ''))).classes('w-full')

        def save_settings():
            """設定を保存."""
            new_settings = {
                'target_dir': str(target_input.value or ''),
                'doc_dir': str(doc_input.value or ''),
            }
            backend.update_user_settings(new_settings)
            app.storage.user['user_settings'] = new_settings
            ui.notify('設定を保存しました')

        async def rebuild_database():
            """データベースを再構築."""
            ui.notify('データベース再構築を開始します...')
            try:
                success, message = await backend.rebuild_db()
                if success:
                    ui.notify(message)
                    backend._sync_statistics()
                    # stats_labelsを更新
                    if stats_labels:
                        stats = backend.get_document_service().get_statistics()
                        if 'chunks' in stats_labels:
                            stats_labels['chunks'].set_text(f'総チャンク数: {stats.get("total_chunks", 0)}')
                        if 'vector' in stats_labels:
                            stats_labels['vector'].set_text(f'ベクトルストア: {"ロード済み" if stats.get("vector_store_loaded", False) else "未ロード"}')
                        if 'lm' in stats_labels:
                            stats_labels['lm'].set_text(f'LM Studio: {"接続済み" if stats.get("lm_connected", False) else "未接続"}')
                        if 'model' in stats_labels:
                            stats_labels['model'].set_text(f'モデル: {stats.get("model", "N/A")}')
                    ui.notify('データベースを再構築しました')
                else:
                    if 'No models loaded' in message:
                        ui.notify(
                            '再構築に失敗しました: LM StudioにEmbeddingモデルがロードされていません。\n'
                            'LM StudioでEmbeddingモデル（例: nomic-embed-text）をロードしてから再試行してください。',
                            color='red', timeout=15000
                        )
                    else:
                        ui.notify(f'再構築に失敗しました: {message}', color='red')
            except Exception as e:
                error_msg = str(e)
                if 'No models loaded' in error_msg:
                    ui.notify(
                        'エラー: LM StudioにEmbeddingモデルがロードされていません。\n'
                        'LM StudioでEmbeddingモデル（例: nomic-embed-text）をロードしてから再試行してください。',
                        color='red', timeout=15000
                    )
                else:
                    ui.notify(f'エラーが発生しました: {error_msg}', color='red')

        # ボタンを上下に配置
        with ui.column().classes('w-full gap-2'):
            ui.button('保存', on_click=save_settings).props('color=blue-500').classes('w-full')
            ui.button('データベース再構築', on_click=rebuild_database).props('color=orange-500').classes('w-full')


def _render_stats(
    container: ui.column,
    backend: RAGBackend,
) -> Dict[str, ui.label]:
    """統計情報を表示."""
    stats_labels: Dict[str, ui.label] = {}

    stats = backend.get_document_service().get_statistics()
    with container:
        stats_labels['chunks'] = ui.label(f'総チャンク数: {stats.get("total_chunks", 0)}').classes('text-white')
        stats_labels['vector'] = ui.label(f'ベクトルストア: {"ロード済み" if stats.get("vector_store_loaded", False) else "未ロード"}').classes('text-white')
        stats_labels['lm'] = ui.label(f'LM Studio: {"接続済み" if stats.get("lm_connected", False) else "未接続"}').classes('text-white')
        stats_labels['model'] = ui.label(f'モデル: {stats.get("model", "N/A")}').classes('text-white')

    # ui.timerで定期的にステータスを更新
    try:
        async def update_status():
            """ステータスを更新."""
            try:
                await backend.check_lm_studio()
                stats = backend.get_document_service().get_statistics()

                if 'chunks' in stats_labels:
                    stats_labels['chunks'].set_text(f'総チャンク数: {stats.get("total_chunks", 0)}')
                if 'vector' in stats_labels:
                    stats_labels['vector'].set_text(f'ベクトルストア: {"ロード済み" if stats.get("vector_store_loaded", False) else "未ロード"}')
                if 'lm' in stats_labels:
                    stats_labels['lm'].set_text(f'LM Studio: {"接続済み" if stats.get("lm_connected", False) else "未接続"}')
                if 'model' in stats_labels:
                    stats_labels['model'].set_text(f'モデル: {stats.get("model", "N/A")}')
            except Exception:
                pass

        ui.timer(3.0, update_status)
    except RuntimeError:
        pass

    return stats_labels