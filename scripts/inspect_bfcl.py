"""Inspect downloaded BFCL simple + multiple data."""
import json

def read_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

print("=" * 70)
print("BFCL v3 Simple")
print("=" * 70)
simple = read_jsonl("data/bfcl/BFCL_v3_simple.json")
print(f"Total tasks: {len(simple)}")
print(f"\nKeys: {list(simple[0].keys())}")
print(f"\n--- Task 1 ---")
t = simple[0]
print(f"  id: {t.get('id', 'N/A')}")
# Function definitions
funcs = t.get("function", t.get("functions", []))
if funcs:
    print(f"  Number of function defs: {len(funcs)}")
    f0 = funcs[0]
    print(f"  Function name: {f0.get('name', 'N/A')}")
    print(f"  Description: {str(f0.get('description', ''))[:100]}...")
    params = f0.get("parameters", {})
    props = params.get("properties", {})
    print(f"  Parameters: {list(props.keys())}")
    for pname, pschema in list(props.items())[:3]:
        print(f"    - {pname}: {pschema}")
    req = params.get("required", [])
    print(f"  Required: {req}")

# Question
print(f"\n  Question: {str(t.get('question', t.get('user_request', '')))[:150]}")

# Check for ground truth
print(f"\n  Ground truth key candidates:")
for k in t.keys():
    if k not in ("function", "functions", "question"):
        val = t[k]
        print(f"    {k}: {str(val)[:120]}")

# Load answers
print(f"\n--- Answers ---")
try:
    answers = read_jsonl("data/bfcl/possible_answer/BFCL_v3_simple.json")
    print(f"Total answers: {len(answers)}")
    print(f"Answer 1: {str(answers[0])[:300]}")
except Exception as e:
    print(f"Error loading answers: {e}")

print("\n" + "=" * 70)
print("BFCL v3 Multiple")
print("=" * 70)
multiple = read_jsonl("data/bfcl/BFCL_v3_multiple.json")
print(f"Total tasks: {len(multiple)}")
t = multiple[0]
print(f"\nKeys: {list(t.keys())}")
funcs = t.get("function", t.get("functions", []))
print(f"Number of function defs: {len(funcs)}")
for i, f in enumerate(funcs[:4]):
    props = f.get("parameters", {}).get("properties", {})
    print(f"  Func {i+1}: {f.get('name', 'N/A')} -> params: {list(props.keys())}")
print(f"\nQuestion: {str(t.get('question', ''))[:150]}")

try:
    answers_m = read_jsonl("data/bfcl/possible_answer/BFCL_v3_multiple.json")
    print(f"\nTotal answers: {len(answers_m)}")
    print(f"Answer 1: {str(answers_m[0])[:300]}")
except Exception as e:
    print(f"Error: {e}")
