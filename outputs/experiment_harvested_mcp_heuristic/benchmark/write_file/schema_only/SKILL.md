# write_file

**Condition:** `schema_only`

## Summary
Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

## Arguments
- `path`, string, required: No description provided.
- `content`, string, required: No description provided.

## Argument template
```json
{
  "path": "data/sample.txt",
  "content": "sample_content_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid call for write_file
```json
{
  "path": "data/sample.txt",
  "content": "sample_content_1"
}
```
- Schema-aligned full call for write_file
```json
{
  "path": "data/sample.txt",
  "content": "sample_content_2"
}
```
