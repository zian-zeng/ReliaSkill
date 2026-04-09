# create_relations

**Condition:** `retrieved_memory`

## Summary
Create multiple new relations between entities in the knowledge graph. Relations should be in active voice

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `relations`, array, required: No description provided.

## Argument template
```json
{
  "relations": [
    {}
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for create_relations
```json
{
  "relations": [
    {}
  ]
}
```
