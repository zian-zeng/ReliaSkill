# search_nodes

**Condition:** `retrieved_memory`

## Summary
Search for nodes in the knowledge graph based on a query

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `query`, string, required: No description provided.

## Argument template
```json
{
  "query": "sample query"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for search_nodes
```json
{
  "query": "sample query"
}
```
