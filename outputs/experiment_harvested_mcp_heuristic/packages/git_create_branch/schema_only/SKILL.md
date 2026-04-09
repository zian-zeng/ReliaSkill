# git_create_branch

**Condition:** `schema_only`

## Summary
Creates a new branch from an optional base branch

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for git_create_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name"
}
```
- Schema-aligned full call for git_create_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name",
  "base_branch": "sample_base_branch_2"
}
```
