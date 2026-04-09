# git_show

**Condition:** `retrieved_docs`

## Summary
Shows the contents of a commit git_show

## When to use
- Shows the contents of a commit
- git_show
- repo_path required
- revision required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

## Arguments
- `repo_path`, string, required: No description provided.
- `revision`, string, required: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "revision": "sample_revision_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Retrieved-docs minimal call for git_show
```json
{
  "repo_path": "data/sample.txt",
  "revision": "sample_revision_1"
}
```
- Retrieved-docs fuller call for git_show
```json
{
  "repo_path": "data/sample.txt",
  "revision": "sample_revision_2"
}
```
