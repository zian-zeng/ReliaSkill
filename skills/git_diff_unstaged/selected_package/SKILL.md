# git_diff_unstaged

**Condition:** `multi_candidate_skill`

## Summary
Shows changes in the working directory that are not yet staged. Provide the required field `repo_path`.

## When to use
- Use `git_diff_unstaged` when the user's request directly matches this tool's purpose.
- Provide the required field `repo_path`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

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
- Minimal valid request that satisfies the required fields for git_diff_unstaged
```json
{
  "repo_path": "data/sample.txt"
}
```
- Richer invocation that uses optional controls for git_diff_unstaged
```json
{
  "repo_path": "data/sample.txt",
  "context_lines": 2
}
```
