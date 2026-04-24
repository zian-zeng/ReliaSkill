import json

lines = open("data/eval/unified_routing_benchmark.jsonl", encoding="utf-8").readlines()

# Count by split
split_counts = {}
for line in lines:
    s = json.loads(line)["split"]
    split_counts[s] = split_counts.get(s, 0) + 1

# Collect first 2 per split
by_split = {}
for line in lines:
    obj = json.loads(line)
    split = obj["split"]
    if split not in by_split:
        by_split[split] = []
    if len(by_split[split]) < 2:
        by_split[split].append(obj)

for split, tasks in by_split.items():
    print(f"\n{'='*60}")
    print(f"SPLIT: {split}  (total tasks: {split_counts[split]})")
    print(f"{'='*60}")
    for i, t in enumerate(tasks):
        print(f"\n--- Task {i+1} ---")
        print(f"  task_id:              {t['task_id']}")
        print(f"  tool_name:            {t['tool_name']}")
        print(f"  user_request:         {t['user_request'][:120]}...")
        print(f"  expected_arguments:   {t['expected_arguments']}")
        print(f"  argument_candidates:  {t['expected_argument_candidates']}")
        print(f"  tags:                 {t['tags']}")
