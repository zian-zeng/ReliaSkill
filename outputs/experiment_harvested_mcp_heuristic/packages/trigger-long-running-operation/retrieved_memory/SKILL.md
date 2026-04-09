# trigger-long-running-operation

**Condition:** `retrieved_memory`

## Summary
Demonstrates a long running operation with progress updates.

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `duration`, string, required: No description provided.
- `steps`, number, required: No description provided.

## Argument template
```json
{
  "duration": "sample_duration_1",
  "steps": 1.0
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for trigger-long-running-operation
```json
{
  "duration": "sample_duration_1",
  "steps": 1.0
}
```
