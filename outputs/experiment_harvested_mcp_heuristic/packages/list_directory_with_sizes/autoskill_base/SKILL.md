# list_directory_with_sizes

**Condition:** `autoskill_base`

## Summary
Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within a directory. Only works within allowed directories. Provide all required fields: `path`, and `sortBy`.

## When to use
- Use `list_directory_with_sizes` when the user's request directly matches this tool's purpose.
- Provide all required fields: `path`, and `sortBy`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `sortBy`: 'name', 'size'.
- Do not let semantic cues override explicit user-provided field values.

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
```json
{
  "sortBy": {
    "name": "name",
    "size": "size"
  }
}
```

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
