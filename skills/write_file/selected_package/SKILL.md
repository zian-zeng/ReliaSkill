# write_file

**Condition:** `multi_candidate_skill`

## Summary
Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories. Provide all required fields: `path`.

## When to use
- Use `write_file` when the user's request directly matches this tool's purpose.
- Provide all required fields: `path`, and `content`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `path`, string, required: Destination file path within an allowed directory.
- `content`, string, required: Full file contents to write.

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
- Minimal valid request that satisfies the required fields for write_file
```json
{
  "path": "data/sample.txt",
  "content": "sample_content_1"
}
```
- Richer invocation that uses optional controls for write_file
```json
{
  "path": "data/sample.txt",
  "content": "sample_content_2"
}
```
