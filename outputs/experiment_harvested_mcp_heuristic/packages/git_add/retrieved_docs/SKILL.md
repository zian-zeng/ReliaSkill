# git_add

**Condition:** `retrieved_docs`

## Summary
Adds file contents to the staging area git_add

## When to use
- Adds file contents to the staging area
- git_add
- repo_path required
- files required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

## Arguments
- `repo_path`, string, required: No description provided.
- `files`, array, required: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "files": [
    "data/sample.txt"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Retrieved-docs minimal call for git_add
```json
{
  "repo_path": "data/sample.txt",
  "files": [
    "data/sample.txt"
  ]
}
```
