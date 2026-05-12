# git_diff_staged

**Condition:** `multi_candidate_skill`

## Summary
Shows changes that are staged for commit. Provide the required field `repo_path`.

## When to use
- Use `git_diff_staged` when the user's request directly matches this tool's purpose.
- Provide the required field `repo_path`.
- Optional control is available through `context_lines` when the request needs extra specificity.
- Use only when the request clearly needs `git_diff_staged`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use for adjacent tools with similar names, descriptions, or arguments.
- Do not use for read/write, search/fetch, create/update, delete/preview, or execute/explain mismatches.
- If the request lacks required fields, abstain or ask for clarification.

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
- Minimal valid request that satisfies the required fields for git_diff_staged
```json
{
  "repo_path": "data/sample.txt"
}
```
- Richer invocation that uses optional controls for git_diff_staged
```json
{
  "repo_path": "data/sample.txt",
  "context_lines": 2
}
```
