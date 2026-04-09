# git_status

**Condition:** `autoskill_base`

## Summary
Shows the working tree status. Provide the required field `repo_path`.

## When to use
- Use `git_status` when the user's request directly matches this tool's purpose.
- Provide the required field `repo_path`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
- Minimal valid request that satisfies the required fields for git_status
```json
{
  "repo_path": "data/sample.txt"
}
```
- Richer invocation that uses optional controls for git_status
```json
{
  "repo_path": "data/sample.txt"
}
```
