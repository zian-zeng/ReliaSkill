# get-sum

**Condition:** `retrieved_memory`

## Summary
Returns the sum of two numbers

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `a`, number, required: No description provided.
- `b`, number, required: No description provided.

## Argument template
```json
{
  "a": 1.0,
  "b": 1.0
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for get-sum
```json
{
  "a": 1.0,
  "b": 1.0
}
```
