# create_directory

**Condition:** `multi_candidate_skill`

## Summary
Create a new directory or ensure a directory exists. Can create multiple nested directories in one operation. If the directory already exists, this operation will succeed silently. Perfect for setting up directory structures for projects or ensuring required paths exist. Only works within allowed directories. Provide the required field `path`.

## When to use
- Use `create_directory` when the user's request directly matches this tool's purpose.
- Provide the required field `path`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `path`, string, required: Directory path to create within an allowed directory.

## Argument template
```json
{
  "path": "data/sample.txt"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for create_directory
```json
{
  "path": "data/sample.txt"
}
```
- Richer invocation that uses optional controls for create_directory
```json
{
  "path": "data/sample.txt"
}
```
- Required-argument dev behavior example.
```json
{
  "path": "data/sample.txt"
}
```
