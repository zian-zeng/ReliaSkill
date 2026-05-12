# list_directory_with_sizes

**Condition:** `multi_candidate_skill`

## Summary
Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within.

## When to use
- Use `list_directory_with_sizes` when the user's request directly matches this tool's purpose.
- Provide all required fields: `path`, and `sortBy`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `sortBy`: 'name', 'size'.
- Do not use when required inputs are missing.

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
- Minimal valid request that satisfies the required fields for list_directory_with_sizes
```json
{
  "path": "data/sample.txt",
  "sortBy": "name"
}
```
- Richer invocation that uses optional controls for list_directory_with_sizes
```json
{
  "path": "data/sample.txt",
  "sortBy": "size"
}
```
