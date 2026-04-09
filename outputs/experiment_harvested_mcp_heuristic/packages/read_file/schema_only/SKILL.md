# read_file

**Condition:** `schema_only`

## Summary
Read the complete contents of a file as text. DEPRECATED: Use read_text_file instead.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for read_file
```json
{
  "path": "data/sample.txt"
}
```
- Schema-aligned full call for read_file
```json
{
  "path": "data/sample.txt",
  "tail": 2.0,
  "head": 2.0
}
```
