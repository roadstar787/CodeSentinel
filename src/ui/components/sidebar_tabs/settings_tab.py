"""設定タブUIコンポーネント"""

from typing import Any, Dict, Optional

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
            ui.button(
                'データベース再構築',
                on_click=lambda: _rebuild_database(backend, stats_labels or {})
            ).props('color=orange-500').classes('w-full')

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
    stats_labels: Dict[str, ui.label],
) -> None:
    """データベースを再構築."""
    ui.notify('データベース再構築を開始します...')
    if not backend:
        ui.notify('バックエンドが利用できません', color='red')
        return

    try:
        success, message = await backend.rebuild_db()
        if success:
            ui.notify(message)
            # 統計情報を更新
            _update_stats_labels(backend, stats_labels)
            ui.notify('データベースを再構築しました')
        else:
            _handle_rebuild_failure(message)
    except Exception as e:
        _handle_rebuild_exception(str(e))


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
        ui.notify(
            '再構築に失敗しました: LM StudioにEmbeddingモデルがロードされていません。\n'
            'LM StudioでEmbeddingモデル（例: nomic-embed-text）をロードしてから再試行してください。',
            color='red',
            timeout=15000,
        )
    else:
        ui.notify(f'再構築に失敗しました: {message}', color='red')


def _handle_rebuild_exception(error_msg: str) -> None:
    """再構築例外時のハンドリング."""
    if 'No models loaded' in error_msg:
        ui.notify(
            'エラー: LM StudioにEmbeddingモデルがロードされていません。\n'
            'LM StudioでEmbeddingモデル（例: nomic-embed-text）をロードしてから再試行してください。',
            color='red',
            timeout=15000,
        )
    else:
        ui.notify(f'エラーが発生しました: {error_msg}', color='red')