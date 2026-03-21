import pytest
import re
from ui.components.chat import render_message
from unittest.mock import MagicMock

def test_mermaid_regex_split():
    # 改良版正規表現の動作テスト
    display_text = "Before\n```mermaid\ngraph TD\nA-->B\n```\nAfter"
    parts = re.split(r'(```mermaid\s*[\s\S]*?(?:```|$))', display_text)
    assert len(parts) == 3
    assert parts[0] == "Before\n"
    assert "graph TD" in parts[1]
    assert parts[2] == "\nAfter"

def test_mermaid_unclosed_block():
    display_text = "Before\n```mermaid\nclassDiagram\n  class A"
    parts = re.split(r'(```mermaid\s*[\s\S]*?(?:```|$))', display_text)
    # capturing group を含めて re.split すると [before, match, after] が返される
    # この場合 after は空文字列 ''
    assert len(parts) == 3
    assert "class A" in parts[1]
    assert parts[2] == ""

def test_mermaid_escaping_in_render():
    # render_message の内部ロジックをシミュレート
    code_with_generics = "classDiagram\n  class ThreadPool {\n    vector<thread> threads\n  }"
    # chat.py のロジック: code = code.replace('<', '~').replace('>', '~')
    if 'classDiagram' in code_with_generics:
        processed_code = code_with_generics.replace('<', '~').replace('>', '~')
    
    assert "vector~thread~" in processed_code
    assert "<" not in processed_code

def test_mermaid_whitespace_handling():
    display_text = "```mermaid \nclassDiagram\n```"
    parts = re.split(r'(```mermaid\s*[\s\S]*?(?:```|$))', display_text)
    assert len(parts) >= 2
    match = parts[1]
    code = re.sub(r'^```mermaid\s*', '', match)
    code = re.sub(r'```$', '', code).strip()
    assert code == "classDiagram"
