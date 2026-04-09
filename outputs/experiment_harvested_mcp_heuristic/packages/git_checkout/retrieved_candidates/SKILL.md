# git_checkout

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `git_checkout` over nearby tools using cues like git_checkout, switches.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `git_checkout` when the request matches its role.
- Shortlist: git_checkout, git_branch, git_create_branch.
- Switches branches
- Switches branches

## When not to use
- Do not confuse `git_checkout` with `git_branch`: List Git branches
- Do not confuse `git_checkout` with `git_create_branch`: Creates a new branch from an optional base branch

## Arguments
- `repo_path`, string, required: No description provided.
- `branch_name`, string, required: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for git_checkout
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name"
}
```
