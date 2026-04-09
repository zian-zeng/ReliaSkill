# git_checkout

**Condition:** `retrieved_docs`

## Summary
Switches branches git_checkout

## When to use
- Switches branches
- git_checkout
- branch_name required
- repo_path required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for git_checkout
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name"
}
```
