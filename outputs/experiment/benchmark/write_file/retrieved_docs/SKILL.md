# write_file

**Condition:** `retrieved_docs`

## Summary
Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories. path required Destination file path within an allowed directory.

## When to use
- Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories.
- path required Destination file path within an allowed directory.
- content required Full file contents to write.
- Write File

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for write_file
```json
{
  "path": "data/sample.txt",
  "content": "sample_content_1"
}
```
- Retrieved-docs fuller call for write_file
```json
{
  "path": "data/sample.txt",
  "content": "sample_content_2"
}
```
