# list_directory_with_sizes

**Condition:** `schema_only`

## Summary
Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within a directory. Only works within allowed directories.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for list_directory_with_sizes
```json
{
  "path": "data/sample.txt",
  "sortBy": "name"
}
```
- Schema-aligned full call for list_directory_with_sizes
```json
{
  "path": "data/sample.txt",
  "sortBy": "size"
}
```
