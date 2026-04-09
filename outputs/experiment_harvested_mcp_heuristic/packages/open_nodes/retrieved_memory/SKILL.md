# open_nodes

**Condition:** `retrieved_memory`

## Summary
Open specific nodes in the knowledge graph by their names

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `names`, array, required: No description provided.

## Argument template
```json
{
  "names": [
    "sample-name"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for open_nodes
```json
{
  "names": [
    "sample-name"
  ]
}
```
