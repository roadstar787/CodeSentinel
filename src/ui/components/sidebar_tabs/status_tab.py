import psutil
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
    labels = stats_labels if stats_labels is not None else {}
    stats_container = ui.column().classes('w-full')

    _render_stats(stats_container, backend, labels)

    # 定期更新タイマー (CPU, RAM, Status)
    def update_stats():
        _update_stats_ui(backend, labels)

    ui.timer(3.0, update_stats)

    return stats_container


def _render_stats(
    container: ui.column,
    backend: Any,
    stats_labels: Dict[str, ui.label],
) -> None:
    """統計情報を表示."""
    if not backend:
        return

    with container:
        ui.label('SYSTEM STATUS').classes('text-[10px] font-bold text-indigo-400 mb-4 tracking-widest')
        
        # リビジョン
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('Revision').classes('text-[12px] text-slate-400')
            ui.label(backend.stats.get("revision", "v0.4.0")).classes('text-[12px] font-medium text-indigo-400')
        
        # ベクトルDB状態
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('Vector DB').classes('text-[12px] text-slate-400')
            stats_labels['vector_store'] = ui.label('OFFLINE').classes('px-2 py-0.5 rounded text-[10px] font-bold')
        
        # チャンク数
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('Total Chunks').classes('text-[12px] text-slate-400')
            stats_labels['total_chunks'] = ui.label('0').classes('text-[12px] font-medium transition-all')
        
        # 最終更新
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('Last Build').classes('text-[12px] text-slate-400')
            stats_labels['last_rebuild'] = ui.label('Never').classes('text-[12px] font-medium')

        ui.separator().classes('bg-slate-700 my-6 opacity-30')
        
        ui.label('SYSTEM LOAD').classes('text-[10px] font-bold text-indigo-400 mb-4 tracking-widest')
        
        # LM Studio
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('LM Studio').classes('text-[12px] text-slate-400')
            stats_labels['lm_status'] = ui.label('Checking...').classes('px-2 py-0.5 rounded text-[10px] font-bold')
        
        # モデル名
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('Active Model').classes('text-[12px] text-slate-400')
            stats_labels['lm_model'] = ui.label('N/A').classes('text-[12px] font-medium truncate max-w-[120px]')

        # CPU
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('CPU').classes('text-[12px] text-slate-400')
            stats_labels['cpu'] = ui.label('0%').classes('text-[12px] font-medium')
        
        # RAM
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('RAM').classes('text-[12px] text-slate-400')
            stats_labels['ram'] = ui.label('0GB').classes('text-[12px] font-medium')

    # 初回反映
    _update_stats_ui(backend, stats_labels)


def _update_stats_ui(
    backend: Any,
    stats_labels: Dict[str, ui.label],
) -> None:
    """統計情報UIを更新."""
    if not backend or not stats_labels:
        return

    # CPU & RAM (psutil)
    cpu_usage = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    ram_usage = f"{mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB"

    # stats
    stats = backend.stats
    
    # UI反映
    if 'cpu' in stats_labels:
        stats_labels['cpu'].set_text(f"{cpu_usage}%")
    if 'ram' in stats_labels:
        stats_labels['ram'].set_text(ram_usage)
    
    # DB状態
    is_loaded = backend.document_service.vector_store is not None if backend.document_service else False
    if 'vector_store' in stats_labels:
        stats_labels['vector_store'].set_text('ONLINE' if is_loaded else 'OFFLINE')
        stats_labels['vector_store'].classes(replace='bg-green-900/40 text-green-400' if is_loaded else 'bg-red-900/40 text-red-400')
    
    if 'total_chunks' in stats_labels:
        stats_labels['total_chunks'].set_text(str(stats.get("total_chunks", 0)))
    
    if 'last_rebuild' in stats_labels:
        stats_labels['last_rebuild'].set_text(str(stats.get("last_rebuild", "Never")))

    # LM Studio
    lm_connected = stats.get("lm_connected", False)
    if 'lm_status' in stats_labels:
        stats_labels['lm_status'].set_text('ONLINE' if lm_connected else 'OFFLINE')
        stats_labels['lm_status'].classes(replace='bg-green-900/40 text-green-400' if lm_connected else 'bg-red-900/40 text-red-400')
    
    if 'lm_model' in stats_labels:
        stats_labels['lm_model'].set_text(stats.get("model", "N/A"))
