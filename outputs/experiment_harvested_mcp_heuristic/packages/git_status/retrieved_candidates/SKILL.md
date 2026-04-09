# git_status

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `git_status` over nearby tools using cues like git_status, tree, status.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `git_status` when the request matches its role.
- Shortlist: git_status, git_diff_unstaged, git_log.
- Shows the working tree status
- Shows the working tree status

## When not to use
- Do not confuse `git_status` with `git_diff_unstaged`: Shows changes in the working directory that are not yet staged
- Do not confuse `git_status` with `git_log`: Shows the commit logs

## Arguments
- `repo_path`, string, required: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for git_status
```json
{
  "repo_path": "data/sample.txt"
}
```
