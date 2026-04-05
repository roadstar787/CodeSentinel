"""設定タブUIコンポーネント"""

from typing import Any, Callable, Dict, Optional

from nicegui import ui, app


def create_settings_tab(
    backend: Any,
    stats_labels: Optional[Dict[str, ui.label]] = None,
    on_tab_toggle: Optional[Callable[[bool], None]] = None,
) -> ui.column:
    """設定タブを作成する.

    Args:
        backend: RAGBackendインスタンス
        stats_labels: 統計情報ラベル
        on_tab_toggle: タブ切り替え無効化コールバック

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

            # 再構築用コンテナ
            rebuild_button: ui.button = ui.button(
                'データベース再構築',
            ).props('color=orange-500').classes('w-full')

            cancel_button: ui.button = ui.button(
                '中断',
            ).props('color=red-500').classes('w-full')
            cancel_button.set_visibility(False)

            # 進行状況表示
            progress_spinner: ui.spinner = ui.spinner(size='md').props('color=orange')
            progress_spinner.set_visibility(False)

            progress_label: ui.label = ui.label('').classes('text-white text-sm')

            # クリックハンドラを設定（要素作成後に設定）
            rebuild_button.on_click(
                lambda: _rebuild_database(
                    backend, rebuild_button, cancel_button,
                    progress_label, progress_spinner,
                    stats_labels or {}, on_tab_toggle
                )
            )
            cancel_button.on_click(
                lambda: _cancel_rebuild(
                    backend, rebuild_button, cancel_button,
                    progress_label, progress_spinner, on_tab_toggle
                )
            )

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


async def _rebuild_database(
    backend: Any,
    rebuild_button: ui.button,
    cancel_button: ui.button,
    progress_label: ui.label,
    progress_spinner: ui.spinner,
    stats_labels: Dict[str, ui.label],
    on_tab_toggle: Optional[Callable[[bool], None]] = None,
) -> None:
    """データベースを再構築."""
    if not backend:
        ui.notify('バックエンドが利用できません', color='red')
        return

    # UIを更新
    rebuild_button.enabled = False
    rebuild_button.set_text('再構築中...')
    cancel_button.set_visibility(True)
    cancel_button.enabled = True
    progress_spinner.set_visibility(True)
    progress_label.set_text('スキャン開始...')

    # タブを無効化
    if on_tab_toggle:
        on_tab_toggle(False)

    # 進行状況コールバック
    def on_progress(status: str) -> None:
        progress_label.set_text(status)

    try:
        success, message = await backend.rebuild_db(progress_callback=on_progress)
        if success:
            # 統計情報を更新
            _update_stats_labels(backend, stats_labels)
            progress_label.set_text(f'完了: {message}')
            ui.notify(f'データベース再構築が完了しました: {message}', color='positive', timeout=5000)
        else:
            if message == '再構築を中断しました':
                progress_label.set_text('中断しました')
                ui.notify('データベース再構築を中断しました', color='warning', timeout=5000)
            else:
                _handle_rebuild_failure(message)
    except Exception as e:
        error_msg = str(e)
        if 'Connection' in error_msg or 'connection' in error_msg.lower():
            progress_label.set_text('コネクションエラー: LM Studioを確認してください')
            ui.notify(f'コネクションエラーが発生しました: LM Studioが起動しているか確認してください', color='red', timeout=10000)
        else:
            _handle_rebuild_exception(error_msg)
    finally:
        # UIを元に戻す
        rebuild_button.enabled = True
        rebuild_button.set_text('データベース再構築')
        cancel_button.set_visibility(False)
        progress_spinner.set_visibility(False)

        # タブを再有効化
        if on_tab_toggle:
            on_tab_toggle(True)


def _cancel_rebuild(
    backend: Any,
    rebuild_button: ui.button,
    cancel_button: ui.button,
    progress_label: ui.label,
    progress_spinner: ui.spinner,
    on_tab_toggle: Optional[Callable[[bool], None]] = None,
) -> None:
    """再構築を中断."""
    if backend:
        backend.cancel_rebuild()
        progress_label.set_text('中断しています...')
        cancel_button.enabled = False


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