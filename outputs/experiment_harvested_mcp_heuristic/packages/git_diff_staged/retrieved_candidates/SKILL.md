# git_diff_staged

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `git_diff_staged` over nearby tools using cues like git_diff_staged.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `git_diff_staged` when the request matches its role.
- Shortlist: git_diff_staged, git_diff_unstaged, git_log.
- Shows changes that are staged for commit
- Shows changes that are staged for commit

## When not to use
- Do not confuse `git_diff_staged` with `git_diff_unstaged`: Shows changes in the working directory that are not yet staged
- Do not confuse `git_diff_staged` with `git_log`: Shows the commit logs

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
- Minimal routed call for git_diff_staged
```json
{
  "repo_path": "data/sample.txt"
}
```
- Full routed call for git_diff_staged
```json
{
  "repo_path": "data/sample.txt",
  "context_lines": 2
}
```
