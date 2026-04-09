# list_directory_with_sizes

**Condition:** `retrieved_docs`

## Summary
Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within a directory. Only works within allowed directories. List Directory with Sizes

## When to use
- Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within a directory. Only works within allowed directories.
- List Directory with Sizes
- sortBy required Allowed values: name, size.
- path required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for list_directory_with_sizes
```json
{
  "path": "data/sample.txt",
  "sortBy": "name"
}
```
- Retrieved-docs fuller call for list_directory_with_sizes
```json
{
  "path": "data/sample.txt",
  "sortBy": "size"
}
```
