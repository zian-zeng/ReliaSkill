# git_checkout

**Condition:** `multi_candidate_skill`

## Summary
Switches branches. Provide all required fields: `repo_path`, and `branch_name`.

## When to use
- Use `git_checkout` when the user's request directly matches this tool's purpose.
- Provide all required fields: `repo_path`, and `branch_name`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

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
- Minimal valid request that satisfies the required fields for git_checkout
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name"
}
```
- Richer invocation that uses optional controls for git_checkout
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name"
}
```
- Required-argument dev behavior example.
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name"
}
```
