# git_create_branch

**Condition:** `multi_candidate_skill`

## Summary
Creates a new branch from an optional base branch. Provide all required fields: `repo_path`, and `branch_name`.

## When to use
- Use `git_create_branch` when the user's request directly matches this tool's purpose.
- Provide all required fields: `repo_path`, and `branch_name`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

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
- Minimal valid request that satisfies the required fields for git_create_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name"
}
```
- Richer invocation that uses optional controls for git_create_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name",
  "base_branch": "sample_base_branch_2"
}
```
