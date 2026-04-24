"""
Convert BFCL v3 simple + multiple data into AutoSkill's native format.

Outputs:
  data/raw/bfcl_v3_tools.json       — unique tool definitions (MCP ToolIR style)
  data/eval/bfcl_v3_benchmark.jsonl  — evaluation tasks with ground-truth arguments
"""
import json
import itertools
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path("data/bfcl")
OUT_TOOLS = Path("data/raw/bfcl_v3_tools.json")
OUT_TASKS = Path("data/eval/bfcl_v3_benchmark.jsonl")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def extract_user_request(question_field: Any) -> str:
    """Extract plain text from BFCL's question format.
    
    BFCL uses: [[{"role": "user", "content": "..."}]]
    """
    if isinstance(question_field, str):
        return question_field
    if isinstance(question_field, list):
        # Could be [[{role, content}]] or [{role, content}]
        flat = question_field
        while flat and isinstance(flat[0], list):
            flat = flat[0]
        for item in flat:
            if isinstance(item, dict) and item.get("role") == "user":
                return item.get("content", "")
            if isinstance(item, str):
                return item
    return str(question_field)


def convert_function_to_tool(func_def: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a BFCL function definition to AutoSkill ToolIR format."""
    name = func_def.get("name", "unknown")
    description = func_def.get("description", "")
    parameters = func_def.get("parameters", {})
    
    return {
        "server_name": "bfcl_v3",
        "name": name,
        "title": name,
        "summary": description[:100] if description else name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": parameters.get("properties", {}),
            "required": parameters.get("required", []),
        },
        "source_pointer": "bfcl_v3",
    }


def expand_ground_truth(gt_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Expand BFCL ground truth into candidate argument dicts.
    
    BFCL format: {"func_name": {"param1": [val1, val2], "param2": [val3]}}
    → list of all valid combinations of argument values
    """
    candidates = []
    for func_name, args in gt_entry.items():
        if not isinstance(args, dict):
            continue
        # Each param has a list of acceptable values
        param_names = list(args.keys())
        param_value_lists = []
        for pname in param_names:
            vals = args[pname]
            if isinstance(vals, list):
                # Filter out empty strings which mean "parameter not provided"
                non_empty = [v for v in vals if v != "" and v is not None]
                if non_empty:
                    param_value_lists.append(non_empty)
                else:
                    param_value_lists.append(vals)  # Keep as-is
            else:
                param_value_lists.append([vals])
        
        # Generate combinations
        for combo in itertools.product(*param_value_lists):
            candidate = {}
            for pname, pval in zip(param_names, combo):
                if pval != "" and pval is not None:  # Skip empty/None
                    candidate[pname] = pval
            candidates.append(candidate)
        
        # Return the first function's candidates (for tool name extraction too)
        return func_name, candidates
    
    return "", [{}]


def main():
    all_tools: Dict[str, Dict[str, Any]] = {}
    all_tasks: List[Dict[str, Any]] = []
    
    for split_name, question_file, answer_file in [
        ("simple", "BFCL_v3_simple.json", "possible_answer/BFCL_v3_simple.json"),
        ("multiple", "BFCL_v3_multiple.json", "possible_answer/BFCL_v3_multiple.json"),
    ]:
        q_path = DATA_DIR / question_file
        a_path = DATA_DIR / answer_file
        
        if not q_path.exists():
            print(f"  Skipping {split_name}: {q_path} not found")
            continue
        
        questions = read_jsonl(q_path)
        answers = read_jsonl(a_path) if a_path.exists() else []
        
        # Index answers by id
        answer_by_id = {a["id"]: a for a in answers if "id" in a}
        
        print(f"\n--- {split_name} ---")
        print(f"  Questions: {len(questions)}")
        print(f"  Answers:   {len(answers)}")
        
        for q in questions:
            task_id = q.get("id", "")
            user_request = extract_user_request(q.get("question", ""))
            functions = q.get("function", [])
            
            if not user_request or not functions:
                continue
            
            # Register all functions as tools
            for func_def in functions:
                tool = convert_function_to_tool(func_def)
                all_tools[tool["name"]] = tool
            
            # Get ground truth
            answer = answer_by_id.get(task_id, {})
            gt_list = answer.get("ground_truth", [])
            
            if gt_list and isinstance(gt_list, list) and isinstance(gt_list[0], dict):
                correct_tool_name, candidates = expand_ground_truth(gt_list[0])
            else:
                # Fallback: use first function as the correct tool
                correct_tool_name = functions[0].get("name", "")
                candidates = [{}]
            
            # Build task record
            task = {
                "task_id": f"bfcl_{task_id}",
                "tool_name": correct_tool_name,
                "user_request": user_request,
                "expected_arguments": candidates[0] if candidates else {},
                "expected_argument_candidates": candidates,
                "split": split_name,
                "tags": ["bfcl_v3", split_name],
            }
            all_tasks.append(task)
    
    # Write tools
    tools_list = list(all_tools.values())
    OUT_TOOLS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_TOOLS.open("w", encoding="utf-8") as f:
        json.dump(tools_list, f, indent=2, ensure_ascii=False)
    
    # Write tasks
    OUT_TASKS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_TASKS.open("w", encoding="utf-8") as f:
        for task in all_tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Conversion complete!")
    print(f"{'='*60}")
    print(f"  Tools:  {len(tools_list)} unique tools → {OUT_TOOLS}")
    print(f"  Tasks:  {len(all_tasks)} tasks → {OUT_TASKS}")
    
    # Stats
    with_args = sum(1 for t in all_tasks if t["expected_arguments"])
    print(f"  Tasks with arguments: {with_args}/{len(all_tasks)} ({100*with_args/len(all_tasks):.1f}%)")
    
    # Sample
    sample = all_tasks[0]
    print(f"\n  Sample task:")
    print(f"    task_id:   {sample['task_id']}")
    print(f"    tool_name: {sample['tool_name']}")
    print(f"    request:   {sample['user_request'][:80]}...")
    print(f"    args:      {sample['expected_arguments']}")
    print(f"    candidates:{len(sample['expected_argument_candidates'])}")


if __name__ == "__main__":
    main()
