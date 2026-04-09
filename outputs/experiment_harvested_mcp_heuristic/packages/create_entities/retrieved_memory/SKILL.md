# create_entities

**Condition:** `retrieved_memory`

## Summary
Create multiple new entities in the knowledge graph

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `entities`, array, required: No description provided.

## Argument template
```json
{
  "entities": [
    {}
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for create_entities
```json
{
  "entities": [
    {}
  ]
}
```
