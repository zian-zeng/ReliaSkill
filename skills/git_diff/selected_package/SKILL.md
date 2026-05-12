# git_diff

**Condition:** `multi_candidate_skill`

## Summary
Shows differences between branches or commits. Provide all required fields: `repo_path`, and `target`.

## When to use
- Use `git_diff` when the user's request directly matches this tool's purpose.
- Provide all required fields: `repo_path`, and `target`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `repo_path`, string, required: No description provided.
- `target`, string, required: No description provided.
- `context_lines`, integer, optional: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "target": "sample_target_1",
  "context_lines": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for git_diff
```json
{
  "repo_path": "data/sample.txt",
  "target": "sample_target_1"
}
```
- Richer invocation that uses optional controls for git_diff
```json
{
  "repo_path": "data/sample.txt",
  "target": "sample_target_2",
  "context_lines": 2
}
```
