# git_branch

**Condition:** `autoskill_base`

## Summary
List Git branches. Provide all required fields: `repo_path`, and `branch_type`.

## When to use
- Use `git_branch` when the user's request directly matches this tool's purpose.
- Provide all required fields: `repo_path`, and `branch_type`.
- Optional controls include `contains`, `not_contains`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

## Arguments
- `repo_path`, string, required: The path to the Git repository.
- `branch_type`, string, required: Whether to list local branches ('local'), remote branches ('remote') or all branches('all').
- `contains`, string, optional: The commit sha that branch should contain. Do not pass anything to this param if no commit sha is specified
- `not_contains`, string, optional: The commit sha that branch should NOT contain. Do not pass anything to this param if no commit sha is specified

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "branch_type": "sample_branch_type_1",
  "contains": "sample_contains_1",
  "not_contains": "sample_not_contains_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for git_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_type": "sample_branch_type_1"
}
```
- Richer invocation that uses optional controls for git_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_type": "sample_branch_type_2",
  "contains": "sample_contains_2",
  "not_contains": "sample_not_contains_2"
}
```
