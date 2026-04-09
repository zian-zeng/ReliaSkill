# git_diff

**Condition:** `retrieved_docs`

## Summary
Shows differences between branches or commits git_diff

## When to use
- Shows differences between branches or commits
- git_diff
- context_lines optional
- repo_path required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for git_diff
```json
{
  "repo_path": "data/sample.txt",
  "target": "sample_target_1"
}
```
- Retrieved-docs fuller call for git_diff
```json
{
  "repo_path": "data/sample.txt",
  "target": "sample_target_2",
  "context_lines": 2
}
```
