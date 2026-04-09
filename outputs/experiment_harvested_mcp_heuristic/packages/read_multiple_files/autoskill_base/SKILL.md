# read_multiple_files

**Condition:** `autoskill_base`

## Summary
Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories. Provide the required field `paths`.

## When to use
- Use `read_multiple_files` when the user's request directly matches this tool's purpose.
- Provide the required field `paths`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
- Minimal valid request that satisfies the required fields for read_multiple_files
```json
{
  "paths": [
    "data/sample.txt"
  ]
}
```
- Richer invocation that uses optional controls for read_multiple_files
```json
{
  "paths": [
    "data/sample.txt"
  ]
}
```
