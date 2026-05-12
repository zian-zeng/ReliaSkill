# read_text_file

**Condition:** `multi_candidate_skill`

## Summary
Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a.

## When to use
- Use `read_text_file` when the user's request directly matches this tool's purpose.
- Provide the required field `path`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `path`, string, required: Path to the file within an allowed directory.
- `tail`, number, optional: If provided, returns only the last N lines of the file.
- `head`, number, optional: If provided, returns only the first N lines of the file.

## Argument template
```json
{
  "path": "data/sample.txt",
  "tail": 1.0,
  "head": 1.0
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for read_text_file
```json
{
  "path": "data/sample.txt"
}
```
- Richer invocation that uses optional controls for read_text_file
```json
{
  "path": "data/sample.txt",
  "tail": 2.0,
  "head": 2.0
}
```
