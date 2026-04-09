# read_media_file

**Condition:** `schema_only`

## Summary
Read an image or audio file. Returns the base64 encoded data and MIME type. Only works within allowed directories.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for read_media_file
```json
{
  "path": "data/sample.txt"
}
```
