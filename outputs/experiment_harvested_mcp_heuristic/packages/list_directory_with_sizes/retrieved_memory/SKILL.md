# list_directory_with_sizes

**Condition:** `retrieved_memory`

## Summary
Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within a directory. Only works within allowed directories.

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `path`, string, required: No description provided.
- `sortBy`, string, required, enum=['name', 'size']: No description provided.

## Argument template
```json
{
  "path": "data/sample.txt",
  "sortBy": "name"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for list_directory_with_sizes
```json
{
  "path": "data/sample.txt",
  "sortBy": "name"
}
```
