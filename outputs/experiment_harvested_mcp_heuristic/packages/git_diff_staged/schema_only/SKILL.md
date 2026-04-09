# git_diff_staged

**Condition:** `schema_only`

## Summary
Shows changes that are staged for commit

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for git_diff_staged
```json
{
  "repo_path": "data/sample.txt"
}
```
- Schema-aligned full call for git_diff_staged
```json
{
  "repo_path": "data/sample.txt",
  "context_lines": 2
}
```
