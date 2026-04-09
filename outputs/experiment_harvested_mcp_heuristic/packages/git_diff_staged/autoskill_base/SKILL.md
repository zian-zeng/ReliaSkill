# git_diff_staged

**Condition:** `autoskill_base`

## Summary
Shows changes that are staged for commit. Provide the required field `repo_path`.

## When to use
- Use `git_diff_staged` when the user's request directly matches this tool's purpose.
- Provide the required field `repo_path`.
- Optional control is available through `context_lines` when the request needs extra specificity.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
