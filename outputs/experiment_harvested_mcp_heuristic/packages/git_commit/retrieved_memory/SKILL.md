# git_commit

**Condition:** `retrieved_memory`

## Summary
Records changes to the repository

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `repo_path`, string, required: No description provided.
- `message`, string, required: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "message": "sample_message_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for git_commit
```json
{
  "repo_path": "data/sample.txt",
  "message": "sample_message_1"
}
```
