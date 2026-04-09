# get_file_info

**Condition:** `autoskill_base`

## Summary
Retrieve detailed metadata about a file or directory. Returns comprehensive information including size, creation time, last modified time, permissions, and type. This tool is perfect for understanding file characteristics without reading the actual content. Only works within allowed directories. Provide the required field `path`.

## When to use
- Use `get_file_info` when the user's request directly matches this tool's purpose.
- Provide the required field `path`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
- Minimal valid request that satisfies the required fields for get_file_info
```json
{
  "path": "data/sample.txt"
}
```
- Richer invocation that uses optional controls for get_file_info
```json
{
  "path": "data/sample.txt"
}
```
