"""データベース再構築スクリプト"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import Settings
from src.core.backend import RAGBackend


async def main():
    """データベースを再構築する."""
    print("データベース再構築を開始します...")
    config = Settings()
    backend = RAGBackend(config)

    print(f"ターゲットディレクトリ: {config.paths.target_dir}")
    print(f"ドキュメントディレクトリ: {config.paths.doc_dir}")
    print(f"データベースパス: {config.paths.db_full_path}")

    success, message = await backend.rebuild_db()

    if success:
        print("データベース再構築が完了しました！")
        print(message)
    else:
        print(f"データベース再構築に失敗しました: {message}")

    # 統計情報を表示
    stats = backend.get_document_service().get_statistics()
    print(f"\n統計情報:")
    print(f"  総チャンク数: {stats['total_chunks']}")
    print(f"  ベクトルストア: {'ロード済み' if stats.get('vector_store_loaded', False) else '未ロード'}")


if __name__ == "__main__":
    asyncio.run(main())