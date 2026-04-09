# git_show

**Condition:** `retrieved_memory`

## Summary
Shows the contents of a commit

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `repo_path`, string, required: No description provided.
- `revision`, string, required: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "revision": "sample_revision_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for git_show
```json
{
  "repo_path": "data/sample.txt",
  "revision": "sample_revision_1"
}
```
