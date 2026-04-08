# read_text_file

**Condition:** `schema_only`

## Summary
Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the head parameter to read only the first N lines of a file, or the tail parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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

## Examples
- Minimal valid call for read_text_file
```json
{
  "path": "data/sample.txt"
}
```
- Schema-aligned full call for read_text_file
```json
{
  "path": "data/sample.txt",
  "tail": 2.0,
  "head": 2.0
}
```
