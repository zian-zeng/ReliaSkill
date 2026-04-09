# read_media_file

**Condition:** `retrieved_docs`

## Summary
Read an image or audio file. Returns the base64 encoded data and MIME type. Only works within allowed directories. Read Media File

## When to use
- Read an image or audio file. Returns the base64 encoded data and MIME type. Only works within allowed directories.
- Read Media File
- path required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for read_media_file
```json
{
  "path": "data/sample.txt"
}
```
