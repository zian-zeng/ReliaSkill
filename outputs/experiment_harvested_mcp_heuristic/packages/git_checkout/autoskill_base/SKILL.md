# git_checkout

**Condition:** `autoskill_base`

## Summary
Switches branches. Provide all required fields: `repo_path`, and `branch_name`.

## When to use
- Use `git_checkout` when the user's request directly matches this tool's purpose.
- Provide all required fields: `repo_path`, and `branch_name`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
- Minimal valid request that satisfies the required fields for git_checkout
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name"
}
```
- Richer invocation that uses optional controls for git_checkout
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name"
}
```
