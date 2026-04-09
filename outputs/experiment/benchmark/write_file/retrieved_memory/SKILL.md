# write_file

**Condition:** `retrieved_memory`

## Summary
Save quoted text to a destination file path.

## When to use
- Retrieve similar skill examples from memory before filling arguments.
- Save quoted text to a destination file path.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `path`, string, required: Destination file path within an allowed directory.
- `content`, string, required: Full file contents to write.

## Argument template
```json
{
  "path": "data/sample.txt",
  "content": "sample_content_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for write_file
```json
{
  "path": "data/sample.txt",
  "content": "sample_content_1"
}
```
- Save quoted text to a destination file path.
```json
{
  "path": "docs/notes.txt",
  "content": "Release checklist"
}
```
