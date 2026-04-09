# write_file

**Condition:** `retrieved_docs`

## Summary
Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories. Write File

## When to use
- Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories.
- Write File
- content required
- path required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
