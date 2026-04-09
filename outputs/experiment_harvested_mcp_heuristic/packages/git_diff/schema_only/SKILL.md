# git_diff

**Condition:** `schema_only`

## Summary
Shows differences between branches or commits

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

## Arguments
- `repo_path`, string, required: No description provided.
- `target`, string, required: No description provided.
- `context_lines`, integer, optional: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "target": "sample_target_1",
  "context_lines": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid call for git_diff
```json
{
  "repo_path": "data/sample.txt",
  "target": "sample_target_1"
}
```
- Schema-aligned full call for git_diff
```json
{
  "repo_path": "data/sample.txt",
  "target": "sample_target_2",
  "context_lines": 2
}
```
