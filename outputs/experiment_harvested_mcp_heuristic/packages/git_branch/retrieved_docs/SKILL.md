# git_branch

**Condition:** `retrieved_docs`

## Summary
not_contains optional The commit sha that branch should NOT contain. Do not pass anything to this param if no commit sha is specified contains optional The commit sha that branch should contain. Do not pass anything to this param if no commit sha is specified

## When to use
- not_contains optional The commit sha that branch should NOT contain. Do not pass anything to this param if no commit sha is specified
- contains optional The commit sha that branch should contain. Do not pass anything to this param if no commit sha is specified
- branch_type required Whether to list local branches ('local'), remote branches ('remote') or all branches('all').
- repo_path required The path to the Git repository.

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for git_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_type": "sample_branch_type_1"
}
```
- Retrieved-docs fuller call for git_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_type": "sample_branch_type_2",
  "contains": "sample_contains_2",
  "not_contains": "sample_not_contains_2"
}
```
