# list_directory

**Condition:** `autoskill_base`

## Summary
Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory. Only works within allowed directories. Provide the required field `path`.

## When to use
- Use `list_directory` when the user's request directly matches this tool's purpose.
- Provide the required field `path`.
- Use the semantic hints when the request uses paraphrases rather than exact schema wording.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

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
- Minimal valid request that satisfies the required fields for list_directory
```json
{
  "path": "data/sample.txt"
}
```
- Richer invocation that uses optional controls for list_directory
```json
{
  "path": "data/sample.txt"
}
```
