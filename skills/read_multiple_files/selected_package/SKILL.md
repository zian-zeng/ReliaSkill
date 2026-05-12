# read_multiple_files

**Condition:** `multi_candidate_skill`

## Summary
Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories. Provide the required field `paths`.

## When to use
- Use `read_multiple_files` when the user's request directly matches this tool's purpose.
- Provide the required field `paths`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

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
- Required-argument dev behavior example.
```json
{
  "paths": [
    "data/sample.txt"
  ]
}
```
