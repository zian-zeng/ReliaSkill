# delete_entities

**Condition:** `retrieved_memory`

## Summary
Delete multiple entities and their associated relations from the knowledge graph

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `entityNames`, array, required: No description provided.

## Argument template
```json
{
  "entityNames": [
    "sample-name"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for delete_entities
```json
{
  "entityNames": [
    "sample-name"
  ]
}
```
