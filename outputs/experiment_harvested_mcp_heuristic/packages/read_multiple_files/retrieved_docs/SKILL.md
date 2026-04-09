# read_multiple_files

**Condition:** `retrieved_docs`

## Summary
Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories. Read Multiple Files

## When to use
- Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories.
- Read Multiple Files
- paths required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

## Arguments
- `paths`, array, required: No description provided.

## Argument template
```json
{
  "paths": [
    "data/sample.txt"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Retrieved-docs minimal call for read_multiple_files
```json
{
  "paths": [
    "data/sample.txt"
  ]
}
```
