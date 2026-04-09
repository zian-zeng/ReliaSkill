# git_add

**Condition:** `schema_only`

## Summary
Adds file contents to the staging area

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

## Arguments
- `repo_path`, string, required: No description provided.
- `files`, array, required: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "files": [
    "data/sample.txt"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid call for git_add
```json
{
  "repo_path": "data/sample.txt",
  "files": [
    "data/sample.txt"
  ]
}
```
