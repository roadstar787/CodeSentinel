"""ステータスタブUIコンポーネント"""

from typing import Any, Dict, Optional

from nicegui import ui


def create_status_tab(
    backend: Any,
    stats_labels: Optional[Dict[str, ui.label]] = None,
) -> ui.column:
    """ステータスタブを作成する.

    Args:
        backend: RAGBackendインスタンス
        stats_labels: 統計情報ラベル（更新用）

    Returns:
        ステータスタブのコンテナ

    """
    stats_labels_internal: Dict[str, ui.label] = {}
    stats_container = ui.column().classes('w-full')

    _render_stats(stats_container, backend, stats_labels_internal)

    # 定期更新タイマー
    _start_status_update_timer(backend, stats_labels_internal)

    return stats_container


def _render_stats(
    container: ui.column,
    backend: Any,
    stats_labels: Dict[str, ui.label],
) -> None:
    """統計情報を表示."""
    if not backend:
        return

    stats = backend.get_document_service().get_statistics()
    with container:
        stats_labels['chunks'] = ui.label(
            f'総チャンク数: {stats.get("total_chunks", 0)}'
        ).classes('text-white')
        stats_labels['vector'] = ui.label(
            f'ベクトルストア: {"ロード済み" if stats.get("vector_store_loaded", False) else "未ロード"}'
        ).classes('text-white')
        stats_labels['lm'] = ui.label(
            f'LM Studio: {"接続済み" if stats.get("lm_connected", False) else "未接続"}'
        ).classes('text-white')
        stats_labels['model'] = ui.label(
            f'モデル: {stats.get("model", "N/A")}'
        ).classes('text-white')


def _start_status_update_timer(
    backend: Any,
    stats_labels: Dict[str, ui.label],
) -> None:
    """定期更新タイマーを開始."""
    try:
        async def update_status():
            """ステータスを更新."""
            try:
                if backend:
                    await backend.check_lm_studio()
                    _update_stats_ui(backend, stats_labels)
            except Exception:
                pass

        ui.timer(3.0, update_status)
    except RuntimeError:
        pass


def _update_stats_ui(
    backend: Any,
    stats_labels: Dict[str, ui.label],
) -> None:
    """統計情報UIを更新."""
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


async def _update_stats(
    backend: Any,
    stats_labels: Dict[str, ui.label],
) -> None:
    """統計情報を非同期更新（テスト用）."""
    if backend:
        await backend.check_lm_studio()
        _update_stats_ui(backend, stats_labels)