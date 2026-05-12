# git_commit

**Condition:** `multi_candidate_skill`

## Summary
Records changes to the repository. Provide all required fields: `repo_path`, and `message`.

## When to use
- Use `git_commit` when the user's request directly matches this tool's purpose.
- Provide all required fields: `repo_path`, and `message`.
- Use only when the request clearly needs `git_commit`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use for adjacent tools with similar names, descriptions, or arguments.
- Do not use for read/write, search/fetch, create/update, delete/preview, or execute/explain mismatches.
- If the request lacks required fields, abstain or ask for clarification.

## Arguments
- `repo_path`, string, required: No description provided.
- `message`, string, required: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "message": "sample_message_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for git_commit
```json
{
  "repo_path": "data/sample.txt",
  "message": "sample_message_1"
}
```
- Richer invocation that uses optional controls for git_commit
```json
{
  "repo_path": "data/sample.txt",
  "message": "sample_message_2"
}
```
