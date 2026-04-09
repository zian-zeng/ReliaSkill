# git_create_branch

**Condition:** `retrieved_memory`

## Summary
Creates a new branch from an optional base branch

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `repo_path`, string, required: No description provided.
- `branch_name`, string, required: No description provided.
- `base_branch`, string, optional: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name",
  "base_branch": "sample_base_branch_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for git_create_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name"
}
```
