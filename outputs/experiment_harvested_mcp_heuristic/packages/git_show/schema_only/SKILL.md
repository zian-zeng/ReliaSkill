# git_show

**Condition:** `schema_only`

## Summary
Shows the contents of a commit

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for git_show
```json
{
  "repo_path": "data/sample.txt",
  "revision": "sample_revision_1"
}
```
- Schema-aligned full call for git_show
```json
{
  "repo_path": "data/sample.txt",
  "revision": "sample_revision_2"
}
```
