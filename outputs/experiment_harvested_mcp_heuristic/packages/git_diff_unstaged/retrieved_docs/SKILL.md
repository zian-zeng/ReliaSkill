# git_diff_unstaged

**Condition:** `retrieved_docs`

## Summary
Shows changes in the working directory that are not yet staged git_diff_unstaged

## When to use
- Shows changes in the working directory that are not yet staged
- git_diff_unstaged
- context_lines optional
- repo_path required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for git_diff_unstaged
```json
{
  "repo_path": "data/sample.txt"
}
```
- Retrieved-docs fuller call for git_diff_unstaged
```json
{
  "repo_path": "data/sample.txt",
  "context_lines": 2
}
```
