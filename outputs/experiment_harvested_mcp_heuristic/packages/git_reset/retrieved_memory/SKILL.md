# git_reset

**Condition:** `retrieved_memory`

## Summary
Unstages all staged changes

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `repo_path`, string, required: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for git_reset
```json
{
  "repo_path": "data/sample.txt"
}
```
