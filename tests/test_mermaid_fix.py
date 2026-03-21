import re

def test_extraction(display_text):
    print(f"Testing: {display_text!r}")
    # Regex from updated ui/components/chat.py
    parts = re.split(r'(```\s*mermaid[^\n]*\n[\s\S]*?(?:```|$))', display_text, flags=re.IGNORECASE)
    
    results = []
    for part in parts:
        if part.startswith('```') and 'mermaid' in part.lower():
            code = re.sub(r'^```\s*mermaid[^\n]*\n', '', part, flags=re.IGNORECASE)
            code = re.sub(r'```$', '', code).strip()
            results.append(code)
    return results

# Test cases
test_cases = [
    ("Standard", "Before\n```mermaid\ngraph TD\nA-->B\n```\nAfter", ["graph TD\nA-->B"]),
    ("Case Insensitive", "```MERMAID\nclassDiagram\n```", ["classDiagram"]),
    ("Mixed Case", "```Mermaid\nsequenceDiagram\n```", ["sequenceDiagram"]),
    ("With Label", "```mermaid:class-diagram\nclass A\n```", ["class A"]),
    ("Spaces", "```  mermaid  \ngraph LR\n```", ["graph LR"]),
    ("Unclosed", "Text\n```mermaid\ngraph TD", ["graph TD"]),
    ("Generics", "```mermaid\nclass A {\n  vector<int> v\n}\n```", ["class A {\n  vector<int> v\n}"]),
    ("Multiple", "One\n```mermaid\nA\n```\nTwo\n```mermaid\nB\n```", ["A", "B"])
]

all_passed = True
for name, text, expected in test_cases:
    actual = test_extraction(text)
    if actual == expected:
        print(f"PASS: {name}")
    else:
        print(f"FAIL: {name}")
        print(f"  Expected: {expected!r}")
        print(f"  Actual:   {actual!r}")
        all_passed = False

if all_passed:
    print("\nAll verification tests passed!")
else:
    print("\nSome tests failed.")
    exit(1)
