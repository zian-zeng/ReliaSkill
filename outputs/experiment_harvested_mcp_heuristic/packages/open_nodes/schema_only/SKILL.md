# open_nodes

**Condition:** `schema_only`

## Summary
Open specific nodes in the knowledge graph by their names

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for open_nodes
```json
{
  "names": [
    "sample-name"
  ]
}
```
