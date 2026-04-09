# git_diff_unstaged

**Condition:** `retrieved_memory`

## Summary
Shows changes in the working directory that are not yet staged

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `repo_path`, string, required: No description provided.
- `context_lines`, integer, optional: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "context_lines": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for git_diff_unstaged
```json
{
  "repo_path": "data/sample.txt"
}
```
