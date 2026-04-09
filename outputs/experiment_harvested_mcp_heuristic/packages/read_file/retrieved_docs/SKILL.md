# read_file

**Condition:** `retrieved_docs`

## Summary
Read the complete contents of a file as text. DEPRECATED: Use read_text_file instead. Read File (Deprecated)

## When to use
- Read the complete contents of a file as text. DEPRECATED: Use read_text_file instead.
- Read File (Deprecated)
- path required
- tail optional

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for read_file
```json
{
  "path": "data/sample.txt"
}
```
- Retrieved-docs fuller call for read_file
```json
{
  "path": "data/sample.txt",
  "tail": 2.0,
  "head": 2.0
}
```
