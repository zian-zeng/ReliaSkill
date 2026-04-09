# create_directory

**Condition:** `autoskill_base`

## Summary
Create a new directory or ensure a directory exists. Can create multiple nested directories in one operation. If the directory already exists, this operation will succeed silently. Perfect for setting up directory structures for projects or ensuring required paths exist. Only works within allowed directories. Provide the required field `path`.

## When to use
- Use `create_directory` when the user's request directly matches this tool's purpose.
- Provide the required field `path`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

## Arguments
- `path`, string, required: No description provided.

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
- Ensure-style request for directory creation
```json
{
  "path": "reports/weekly"
}
```
