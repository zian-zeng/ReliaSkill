# git_add

**Condition:** `multi_candidate_skill`

## Summary
Adds file contents to the staging area. Provide all required fields: `repo_path`, and `files`.

## When to use
- Use `git_add` when the user's request directly matches this tool's purpose.
- Provide all required fields: `repo_path`, and `files`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

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
- Minimal valid request that satisfies the required fields for git_add
```json
{
  "repo_path": "data/sample.txt",
  "files": [
    "data/sample.txt"
  ]
}
```
- Richer invocation that uses optional controls for git_add
```json
{
  "repo_path": "data/sample.txt",
  "files": [
    "data/sample.txt"
  ]
}
```
- Required-argument dev behavior example.
```json
{
  "repo_path": "data/sample.txt",
  "files": [
    "data/sample.txt"
  ]
}
```
