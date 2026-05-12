# read_file

**Condition:** `multi_candidate_skill`

## Summary
Read the complete contents of a file as text. DEPRECATED: Use read_text_file instead. Provide the required field `path`.

## When to use
- Use `read_file` when the user's request directly matches this tool's purpose.
- Provide the required field `path`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `path`, string, required: No description provided.
- `tail`, number, optional: No description provided.
- `head`, number, optional: No description provided.

## Argument template
```json
{
  "path": "data/sample.txt",
  "tail": 1.0,
  "head": 1.0
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for read_file
```json
{
  "path": "data/sample.txt"
}
```
- Richer invocation that uses optional controls for read_file
```json
{
  "path": "data/sample.txt",
  "tail": 2.0,
  "head": 2.0
}
```
