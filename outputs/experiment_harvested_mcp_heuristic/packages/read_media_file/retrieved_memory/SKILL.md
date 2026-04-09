# read_media_file

**Condition:** `retrieved_memory`

## Summary
Read an image or audio file. Returns the base64 encoded data and MIME type. Only works within allowed directories.

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

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
- Minimal valid memory-backed call for read_media_file
```json
{
  "path": "data/sample.txt"
}
```
