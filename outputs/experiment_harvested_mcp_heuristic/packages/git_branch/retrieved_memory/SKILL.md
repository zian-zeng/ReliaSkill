# git_branch

**Condition:** `retrieved_memory`

## Summary
List Git branches

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `repo_path`, string, required: The path to the Git repository.
- `branch_type`, string, required: Whether to list local branches ('local'), remote branches ('remote') or all branches('all').
- `contains`, string, optional: The commit sha that branch should contain. Do not pass anything to this param if no commit sha is specified
- `not_contains`, string, optional: The commit sha that branch should NOT contain. Do not pass anything to this param if no commit sha is specified

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "branch_type": "sample_branch_type_1",
  "contains": "sample_contains_1",
  "not_contains": "sample_not_contains_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for git_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_type": "sample_branch_type_1"
}
```
