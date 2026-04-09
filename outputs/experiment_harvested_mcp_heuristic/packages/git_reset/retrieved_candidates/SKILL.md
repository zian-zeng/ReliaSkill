# git_reset

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `git_reset` over nearby tools using cues like git_reset, unstages.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `git_reset` when the request matches its role.
- Shortlist: git_reset, git_diff_staged, git_diff_unstaged.
- Unstages all staged changes
- Unstages all staged changes

## When not to use
- Do not confuse `git_reset` with `git_diff_staged`: Shows changes that are staged for commit
- Do not confuse `git_reset` with `git_diff_unstaged`: Shows changes in the working directory that are not yet staged

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
- Minimal routed call for git_reset
```json
{
  "repo_path": "data/sample.txt"
}
```
