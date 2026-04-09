# read_text_file

**Condition:** `retrieved_memory`

## Summary
Read the top lines of a file when the request asks for the first or opening lines. Read the trailing lines of a file when the request asks for the last or ending lines.

## When to use
- Retrieve similar skill examples from memory before filling arguments.
- Read the top lines of a file when the request asks for the first or opening lines.
- Read the trailing lines of a file when the request asks for the last or ending lines.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

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
- Minimal valid memory-backed call for read_text_file
```json
{
  "path": "data/sample.txt"
}
```
- Read the top lines of a file when the request asks for the first or opening lines.
```json
{
  "path": "src/app.py",
  "head": 8
}
```
- Read the trailing lines of a file when the request asks for the last or ending lines.
```json
{
  "path": "logs/output.txt",
  "tail": 12
}
```
