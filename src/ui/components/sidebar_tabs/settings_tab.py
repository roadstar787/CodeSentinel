"""設定タブUIコンポーネント"""

from typing import Any, Callable, Dict, Optional

from nicegui import ui, app


def create_settings_tab(
    backend: Any,
    stats_labels: Optional[Dict[str, ui.label]] = None,
) -> ui.column:
    """設定タブを作成する.

    Args:
        backend: RAGBackendインスタンス
        stats_labels: 統計情報ラベル

    Returns:
        設定タブのコンテナ

    """
    settings = backend.get_user_settings() if backend else {}

    with ui.column().classes('w-full gap-4') as container:
        ui.label('ターゲットディレクトリ').classes('text-white')
        target_input = ui.input(value=str(settings.get('target_dir', ''))).classes('w-full')

        ui.label('ドキュメントディレクトリ').classes('text-white')
        doc_input = ui.input(value=str(settings.get('doc_dir', ''))).classes('w-full')

        with ui.column().classes('w-full gap-2'):
            ui.button(
                '保存',
                on_click=lambda: _save_settings(backend, target_input, doc_input)
            ).props('color=blue-500').classes('w-full')

            # 再構築用コンテナ (リアクティブ・バインド)
            rebuild_button = ui.button().props('color=orange-500').classes('w-full')
            rebuild_button.bind_text_from(backend.stats, 'is_rebuilding', 
                                        backward=lambda x: '再構築中...' if x else 'データベース再構築')
            rebuild_button.bind_enabled_from(backend.stats, 'is_rebuilding', 
                                          backward=lambda x: not x)

            cancel_button = ui.button('中断').props('color=red-500').classes('w-full')
            cancel_button.bind_visibility_from(backend.stats, 'is_rebuilding')

            # 進行状況表示
            progress_spinner = ui.spinner(size='md').props('color=orange')
            progress_spinner.bind_visibility_from(backend.stats, 'is_rebuilding')

            progress_label = ui.label().classes('text-white text-sm')
            progress_label.bind_text_from(backend.stats, 'status_text')

            # 通知監視タイマー
            def _check_notifications():
                noti = backend.stats.get('last_notification')
                if noti:
                    ui.notify(noti['message'], color=noti.get('color', 'info'), timeout=noti.get('timeout', 5000))
                    backend.stats['last_notification'] = None

            ui.timer(1.0, _check_notifications)

            # クリックハンドラを設定 (バックエンドのみを渡す)
            rebuild_button.on_click(lambda: _rebuild_database(backend))
            cancel_button.on_click(lambda: _cancel_rebuild(backend))

    return container


def _save_settings(
    backend: Any,
    target_input: ui.input,
    doc_input: ui.input,
) -> None:
    """設定を保存."""
    new_settings = {
        'target_dir': str(target_input.value or ''),
        'doc_dir': str(doc_input.value or ''),
    }
    if backend:
        backend.update_user_settings(new_settings)
    try:
        app.storage.user['user_settings'] = new_settings
    except RuntimeError:
        pass
    ui.notify('設定を保存しました')


async def _rebuild_database(backend: Any) -> None:
    """データベースを再構築 (UI非依存版)."""
    if not backend:
        ui.notify('バックエンドが利用できません', color='red')
        return

    # ステート更新 (バインドにより全クライアントに反映)
    backend.stats["status_text"] = "スキャン開始..."
    # is_rebuilding は backend.rebuild_db 内で True に設定される

    try:
        # progress_callback は backend.rebuild_db 内で status_text を更新するようにラップ済み
        success, message = await backend.rebuild_db()
        
        if success:
            backend.stats["status_text"] = f"完了: {message}"
            backend.stats["last_notification"] = {
                "message": f"データベース再構築が完了しました: {message}",
                "color": "positive",
                "timeout": 5000
            }
        else:
            if message == "再構築を中断しました":
                backend.stats["status_text"] = "中断しました"
                backend.stats["last_notification"] = {
                    "message": "データベース再構築を中断しました",
                    "color": "warning",
                    "timeout": 5000
                }
            else:
                error_msg = f"再構築に失敗しました: {message}"
                backend.stats["status_text"] = "失敗"
                backend.stats["last_notification"] = {
                    "message": error_msg,
                    "color": "red",
                    "timeout": 15000
                }
    except Exception as e:
        error_msg = str(e)
        backend.stats["status_text"] = "エラー発生"
        backend.stats["last_notification"] = {
            "message": f"エラーが発生しました: {error_msg}",
            "color": "red",
            "timeout": 15000
        }
    finally:
        # is_rebuilding は backend.rebuild_db の finally で False に設定される
        # 必要ならここで追加のクリーンアップ
        pass


def _cancel_rebuild(backend: Any) -> None:
    """再構築を中断 (UI非依存版)."""
    if backend:
        backend.cancel_rebuild()
        backend.stats["status_text"] = "中断しています..."


def _update_stats_labels(
    backend: Any,
    stats_labels: Dict[str, ui.label],
) -> None:
    """統計情報ラベルを更新."""
    if not backend or not stats_labels:
        return
    stats = backend.get_document_service().get_statistics()
    if 'chunks' in stats_labels:
        stats_labels['chunks'].set_text(f'総チャンク数: {stats.get("total_chunks", 0)}')
    if 'vector' in stats_labels:
        stats_labels['vector'].set_text(
            f'ベクトルストア: {"ロード済み" if stats.get("vector_store_loaded", False) else "未ロード"}'
        )
    if 'lm' in stats_labels:
        stats_labels['lm'].set_text(
            f'LM Studio: {"接続済み" if stats.get("lm_connected", False) else "未接続"}'
        )
    if 'model' in stats_labels:
        stats_labels['model'].set_text(f'モデル: {stats.get("model", "N/A")}')


def _handle_rebuild_failure(message: str) -> None:
    """再構築失敗時のハンドリング."""
    if 'No models loaded' in message:
        error_msg = '再構築に失敗しました: LM StudioにEmbeddingモデルがロードされていません。\nLM StudioでEmbeddingモデル（例: nomic-embed-text）をロードしてから再試行してください。'
    else:
        error_msg = f'再構築に失敗しました: {message}'

    ui.notify(error_msg, color='red', timeout=15000)


def _handle_rebuild_exception(error_msg: str) -> None:
    """再構築例外時のハンドリング."""
    if 'No models loaded' in error_msg:
        message = 'エラー: LM StudioにEmbeddingモデルがロードされていません。\nLM StudioでEmbeddingモデル（例: nomic-embed-text）をロードしてから再試行してください。'
    else:
        message = f'エラーが発生しました: {error_msg}'

    ui.notify(message, color='red', timeout=15000)