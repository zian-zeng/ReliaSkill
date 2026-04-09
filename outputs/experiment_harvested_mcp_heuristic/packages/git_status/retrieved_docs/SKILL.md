# git_status

**Condition:** `retrieved_docs`

## Summary
Shows the working tree status git_status

## When to use
- Shows the working tree status
- git_status
- repo_path required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for git_status
```json
{
  "repo_path": "data/sample.txt"
}
```
