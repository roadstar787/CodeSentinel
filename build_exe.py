import os
import subprocess
import sys
from pathlib import Path
import nicegui

def build():
    # NiceGUIのインストール先を取得
    nicegui_path = Path(nicegui.__file__).parent
    
    # 実行するスクリプトのパス
    main_script = 'CodeSentinel.py'
    
    # PyInstallerのオプション設定
    # --onedir (または -D) は起動が速く安定するため、今回はこれを使用 (-F --onefile は初回起動が遅い)
    # --windowed (-w) はコンソールを表示しない（デバッグ時は外してもよい）
    # --add-data で必要なフォルダを同梱
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm',
        '--name=CodeSentinel',
        '--windowed',  # 製品版ではコンソールを非表示にする
        '--onedir',  # 安定性重視
        '--clean',
        f'--add-data={nicegui_path}{os.pathsep}nicegui',
        f'--add-data=ui{os.pathsep}ui',
        f'--add-data=backend{os.pathsep}backend',
        '--collect-all=langchain',
        '--collect-all=langchain_openai',
        '--collect-all=langchain_community',
        '--collect-all=faiss',
        '--collect-all=nicegui',
        '--collect-all=unstructured',
        '--collect-all=spacy',
        '--collect-all=en_core_web_sm',
        main_script
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

if __name__ == '__main__':
    build()
