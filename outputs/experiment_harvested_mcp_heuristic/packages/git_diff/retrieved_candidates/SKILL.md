# git_diff

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `git_diff` over nearby tools using cues like git_diff, differences, between, commits.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `git_diff` when the request matches its role.
- Shortlist: git_diff, git_branch, git_diff_staged.
- Shows differences between branches or commits
- Shows differences between branches or commits

## When not to use
- Do not confuse `git_diff` with `git_branch`: List Git branches
- Do not confuse `git_diff` with `git_diff_staged`: Shows changes that are staged for commit

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
- Minimal routed call for git_diff
```json
{
  "repo_path": "data/sample.txt",
  "target": "sample_target_1"
}
```
- Full routed call for git_diff
```json
{
  "repo_path": "data/sample.txt",
  "target": "sample_target_2",
  "context_lines": 2
}
```
