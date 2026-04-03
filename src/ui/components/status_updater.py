"""ステータス更新コンポーネント"""

import asyncio
from typing import Callable

import psutil
from nicegui import ui

from src.core.backend import RAGBackend


def create_status_updater() -> Callable:
    """ステータス更新ループを作成する.

    Returns:
        ステータス更新を開始する関数

    """
    def start_status_loop(
        cpu_label: ui.label,
        ram_label: ui.label,
        lm_status_chip: ui.label,
        lm_model_label: ui.label,
        status_chip: ui.label,
        chunk_count_label: ui.label,
        last_update_label: ui.label,
        backend: RAGBackend
    ) -> asyncio.Task:
        """ステータス更新ループを開始する.

        Args:
            cpu_label: CPU使用率表示ラベル
            ram_label: RAM使用量表示ラベル
            lm_status_chip: LM Studio接続状態表示
            lm_model_label: LM Studioモデル名表示
            status_chip: ベクトルDB状態表示
            chunk_count_label: チャンク数表示
            last_update_label: 最終ビルド日時表示
            backend: RAGBackendインスタンス

        Returns:
            実行中の非同期タスク

        """
        async def update_status_loop() -> None:
            """ステータス更新ループ."""
            while True:
                try:
                    # CPU使用率
                    cpu_label.text = f"{psutil.cpu_percent()}%"
                    
                    # RAM使用量
                    mem = psutil.virtual_memory()
                    ram_label.text = f"{mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB"
                    
                    # LM Studio接続確認
                    connected = await backend.check_lm_studio()
                    if connected:
                        lm_status_chip.text = 'ONLINE'
                        lm_status_chip.classes(replace='bg-green-900/40 text-green-400')
                    else:
                        lm_status_chip.text = 'OFFLINE'
                        lm_status_chip.classes(replace='bg-red-900/40 text-red-400')
                    
                    # モデル情報
                    stats = backend.stats
                    lm_model_label.text = stats.get('model', 'N/A')
                    
                    # DB状態
                    is_loaded = backend.vector_store is not None
                    if is_loaded:
                        status_chip.text = 'ONLINE'
                        status_chip.classes(replace='bg-green-900/40 text-green-400')
                    else:
                        status_chip.text = 'OFFLINE'
                        status_chip.classes(replace='bg-red-900/40 text-red-400')
                    
                    # チャンク数
                    chunk_count_label.text = str(stats.get('total_chunks', 0))
                    
                    # 最終ビルド日時
                    last_update_label.text = stats.get('last_rebuild', 'Never')
                    
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"Status update error: {e}")
                    await asyncio.sleep(3)
        
        return asyncio.create_task(update_status_loop())
    
    return start_status_loop