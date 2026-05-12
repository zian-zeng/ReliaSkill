# git_show

**Condition:** `multi_candidate_skill`

## Summary
Shows the contents of a commit. Provide all required fields: `repo_path`, and `revision`.

## When to use
- Use `git_show` when the user's request directly matches this tool's purpose.
- Provide all required fields: `repo_path`, and `revision`.
- Use only when the request clearly needs `git_show`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use for adjacent tools with similar names, descriptions, or arguments.
- Do not use for read/write, search/fetch, create/update, delete/preview, or execute/explain mismatches.
- If the request lacks required fields, abstain or ask for clarification.

## Arguments
- `repo_path`, string, required: No description provided.
- `revision`, string, required: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "revision": "sample_revision_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for git_show
```json
{
  "repo_path": "data/sample.txt",
  "revision": "sample_revision_1"
}
```
- Richer invocation that uses optional controls for git_show
```json
{
  "repo_path": "data/sample.txt",
  "revision": "sample_revision_2"
}
```
