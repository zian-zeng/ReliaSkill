# list_directory

**Condition:** `retrieved_memory`

## Summary
Inspect the contents of a target directory such as docs.

## When to use
- Retrieve similar skill examples from memory before filling arguments.
- Inspect the contents of a target directory such as docs.

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
- Minimal valid memory-backed call for list_directory
```json
{
  "path": "data/sample.txt"
}
```
- Inspect the contents of a target directory such as docs.
```json
{
  "path": "docs"
}
```
