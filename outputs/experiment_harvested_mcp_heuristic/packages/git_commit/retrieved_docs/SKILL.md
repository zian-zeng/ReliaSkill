# git_commit

**Condition:** `retrieved_docs`

## Summary
Records changes to the repository git_commit

## When to use
- Records changes to the repository
- git_commit
- repo_path required
- message required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

## Arguments
- `repo_path`, string, required: No description provided.
- `message`, string, required: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "message": "sample_message_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Retrieved-docs minimal call for git_commit
```json
{
  "repo_path": "data/sample.txt",
  "message": "sample_message_1"
}
```
- Retrieved-docs fuller call for git_commit
```json
{
  "repo_path": "data/sample.txt",
  "message": "sample_message_2"
}
```
