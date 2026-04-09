# echo

**Condition:** `retrieved_memory`

## Summary
Echoes back the input string

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `message`, string, required: No description provided.

## Argument template
```json
{
  "message": "sample_message_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for echo
```json
{
  "message": "sample_message_1"
}
```
