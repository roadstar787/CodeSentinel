import re

def test_regex(display_text):
    print(f"Testing: {display_text!r}")
    # Updated regex to match ui/components/chat.py with IGNORECASE
    parts = re.split(r'(```\s*mermaid[^\n]*\n[\s\S]*?(?:```|$))', display_text, flags=re.IGNORECASE)
    print(f"Parts count: {len(parts)}")
    for i, part in enumerate(parts):
        print(f"Part {i}: {part!r}")
        if part.startswith('```') and 'mermaid' in part.lower():
            code = re.sub(r'^```\s*mermaid[^\n]*\n', '', part, flags=re.IGNORECASE)
            code = re.sub(r'```$', '', code).strip()
            print(f"  Extracted code: {code!r}")

print("--- Test 1: Standard ---")
test_regex("Before\n```mermaid\ngraph TD\nA-->B\n```\nAfter")

print("\n--- Test 2: Space after mermaid ---")
test_regex("Before\n```mermaid \ngraph TD\nA-->B\n```\nAfter")

print("\n--- Test 3: Uppercase Mermaid ---")
test_regex("Before\n```Mermaid\ngraph TD\nA-->B\n```\nAfter")

print("\n--- Test 4: Space before mermaid ---")
test_regex("Before\n``` mermaid\ngraph TD\nA-->B\n```\nAfter")

print("\n--- Test 5: Unclosed ---")
test_regex("Before\n```mermaid\ngraph TD\nA-->B")