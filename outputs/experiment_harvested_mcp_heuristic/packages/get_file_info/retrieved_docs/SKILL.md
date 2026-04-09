# get_file_info

**Condition:** `retrieved_docs`

## Summary
Retrieve detailed metadata about a file or directory. Returns comprehensive information including size, creation time, last modified time, permissions, and type. This tool is perfect for understanding file characteristics without reading the actual content. Only works within allowed directories. Get File Info

## When to use
- Retrieve detailed metadata about a file or directory. Returns comprehensive information including size, creation time, last modified time, permissions, and type. This tool is perfect for understanding file characteristics without reading the actual content. Only works within allowed directories.
- Get File Info
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
- Retrieved-docs minimal call for get_file_info
```json
{
  "path": "data/sample.txt"
}
```
