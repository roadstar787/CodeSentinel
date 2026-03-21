import logging
import sys
from backend.core import RAGBackend

# ログ設定を追加
logging.basicConfig(
    level=logging.WARNING,  # デフォルトはWARNING以上のみ表示
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# NiceGUIのログレベルも設定
logging.getLogger('nicegui').setLevel(logging.WARNING)

def main():
    print("Hello from codesentinel!")


if __name__ == "__main__":
    main()