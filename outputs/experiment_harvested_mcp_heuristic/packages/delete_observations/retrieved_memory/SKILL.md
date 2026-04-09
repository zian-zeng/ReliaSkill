# delete_observations

**Condition:** `retrieved_memory`

## Summary
Delete specific observations from entities in the knowledge graph

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `deletions`, array, required: No description provided.

## Argument template
```json
{
  "deletions": [
    {}
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for delete_observations
```json
{
  "deletions": [
    {}
  ]
}
```
