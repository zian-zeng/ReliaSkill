# git_create_branch

**Condition:** `autoskill_base`

## Summary
Creates a new branch from an optional base branch. Provide all required fields: `repo_path`, and `branch_name`.

## When to use
- Use `git_create_branch` when the user's request directly matches this tool's purpose.
- Provide all required fields: `repo_path`, and `branch_name`.
- Optional control is available through `base_branch` when the request needs extra specificity.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

## Arguments
- `repo_path`, string, required: No description provided.
- `branch_name`, string, required: No description provided.
- `base_branch`, string, optional: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name",
  "base_branch": "sample_base_branch_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for git_create_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name"
}
```
- Richer invocation that uses optional controls for git_create_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name",
  "base_branch": "sample_base_branch_2"
}
```
