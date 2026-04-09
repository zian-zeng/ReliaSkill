# list_directory

**Condition:** `retrieved_docs`

## Summary
Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory. Only works within allowed directories. path required Directory path to inspect within an allowed directory.

## When to use
- Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory. Only works within allowed directories.
- path required Directory path to inspect within an allowed directory.
- List Directory

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

## Arguments
- `path`, string, required: Directory path to inspect within an allowed directory.

## Argument template
```json
{
  "path": "data/sample.txt"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Retrieved-docs minimal call for list_directory
```json
{
  "path": "data/sample.txt"
}
```
