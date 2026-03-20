import pytest
from ui.components.chat import parse_gap_content

def test_parse_normal_json():
    content = """
    分析結果です。
    <gaps>
    [
        {"file": "test.py", "line": 10, "issue": "乖離1", "corrected_code": "print(1)"}
    ]
    </gaps>
    """
    gaps = parse_gap_content(content)
    assert len(gaps) == 1
    assert gaps[0]["file"] == "test.py"
    assert gaps[0]["line"] == 10

def test_parse_truncated_json():
    # 閉じ括弧が欠落しているケース
    content = """
    <gaps>
    [
        {"file": "test.py", "line": 10, "issue": "乖離1", "corrected_code": "print(1)"
    """
    gaps = parse_gap_content(content)
    assert len(gaps) == 1
    assert gaps[0]["file"] == "test.py"

def test_parse_multiple_gaps():
    content = """
    <gaps>
    [
        {"file": "a.py", "issue": "err1"},
        {"file": "b.py", "issue": "err2"}
    ]
    </gaps>
    """
    gaps = parse_gap_content(content)
    assert len(gaps) == 2
    assert gaps[0]["file"] == "a.py"
    assert gaps[1]["file"] == "b.py"

def test_parse_no_gaps():
    content = "単なるチャットメッセージです。"
    gaps = parse_gap_content(content)
    assert gaps == []

def test_parse_empty_gaps():
    content = "<gaps></gaps>"
    gaps = parse_gap_content(content)
    assert gaps == []

def test_parse_repair_malformed_element():
    # 最後の要素が壊れているが前の要素は生きているケース
    content = """
    <gaps>
    [
        {"file": "good.py", "issue": "ok"},
        {"file": "bad.py", "iss
    """
    gaps = parse_gap_content(content)
    # 修復ロジックにより、有効なJSON部分（最初の要素）だけが抽出されることを期待
    assert len(gaps) >= 1
    assert gaps[0]["file"] == "good.py"
