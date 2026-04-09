# write_file

**Condition:** `autoskill_base`

## Summary
Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories. Provide all required fields: `path`, and `content`.

## When to use
- Use `write_file` when the user's request directly matches this tool's purpose.
- Provide all required fields: `path`, and `content`.
- Use the semantic hints when the request uses paraphrases rather than exact schema wording.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

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
```json
{
  "content": {
    "containing the text": "__tail_text__",
    "with content": "__tail_text__",
    "save": "__quoted_text_to_path__",
    "write": "__quoted_text_to_path__"
  }
}
```

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
