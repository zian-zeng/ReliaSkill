# git_branch

**Condition:** `schema_only`

## Summary
List Git branches

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

## Arguments
- `repo_path`, string, required: The path to the Git repository.
- `branch_type`, string, required: Whether to list local branches ('local'), remote branches ('remote') or all branches('all').
- `contains`, string, optional: The commit sha that branch should contain. Do not pass anything to this param if no commit sha is specified
- `not_contains`, string, optional: The commit sha that branch should NOT contain. Do not pass anything to this param if no commit sha is specified

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "branch_type": "sample_branch_type_1",
  "contains": "sample_contains_1",
  "not_contains": "sample_not_contains_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid call for git_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_type": "sample_branch_type_1"
}
```
- Schema-aligned full call for git_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_type": "sample_branch_type_2",
  "contains": "sample_contains_2",
  "not_contains": "sample_not_contains_2"
}
```
