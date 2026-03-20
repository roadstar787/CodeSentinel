import pytest
import os
from pathlib import Path

@pytest.fixture
def temp_workspace(tmp_path):
    """テスト用の一時ディレクトリを作成します。"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace

@pytest.fixture
def sample_python_file(temp_workspace):
    """テスト用のサンプルPythonファイルを作成します。"""
    file_path = temp_workspace / "sample.py"
    file_path.write_text("def hello():\n    print('hello')\n", encoding='utf-8')
    return file_path
