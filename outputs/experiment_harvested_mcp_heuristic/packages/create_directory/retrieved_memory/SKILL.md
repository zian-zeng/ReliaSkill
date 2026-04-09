# create_directory

**Condition:** `retrieved_memory`

## Summary
Ensure a directory exists for reports or generated outputs.

## When to use
- Retrieve similar skill examples from memory before filling arguments.
- Ensure a directory exists for reports or generated outputs.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

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
- Minimal valid memory-backed call for create_directory
```json
{
  "path": "data/sample.txt"
}
```
- Ensure a directory exists for reports or generated outputs.
```json
{
  "path": "reports/weekly"
}
```
