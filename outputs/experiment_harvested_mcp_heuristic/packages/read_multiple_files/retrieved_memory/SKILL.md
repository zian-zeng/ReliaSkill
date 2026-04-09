# read_multiple_files

**Condition:** `retrieved_memory`

## Summary
Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories.

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `paths`, array, required: No description provided.

## Argument template
```json
{
  "paths": [
    "data/sample.txt"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for read_multiple_files
```json
{
  "paths": [
    "data/sample.txt"
  ]
}
```
