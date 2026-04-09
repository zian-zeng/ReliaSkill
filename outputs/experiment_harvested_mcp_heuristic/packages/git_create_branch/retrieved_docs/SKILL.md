# git_create_branch

**Condition:** `retrieved_docs`

## Summary
Creates a new branch from an optional base branch base_branch optional

## When to use
- Creates a new branch from an optional base branch
- base_branch optional
- git_create_branch
- branch_name required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for git_create_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name"
}
```
- Retrieved-docs fuller call for git_create_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name",
  "base_branch": "sample_base_branch_2"
}
```
