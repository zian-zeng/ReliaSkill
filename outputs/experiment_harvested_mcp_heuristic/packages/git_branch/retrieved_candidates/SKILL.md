# git_branch

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `git_branch` over nearby tools using cues like git_branch, branches, repo_path, path.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `git_branch` when the request matches its role.
- Shortlist: git_branch, list_allowed_directories, convert_time.
- List Git branches
- List Git branches

## When not to use
- Do not confuse `git_branch` with `list_allowed_directories`: Returns the list of directories that this server is allowed to access. Subdirectories within these allowed directories are also accessible. Use this to understand which directories and their nested paths are available before trying to access files.
- Do not confuse `git_branch` with `convert_time`: Convert time between timezones

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
- Minimal routed call for git_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_type": "sample_branch_type_1"
}
```
- Full routed call for git_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_type": "sample_branch_type_2",
  "contains": "sample_contains_2",
  "not_contains": "sample_not_contains_2"
}
```
