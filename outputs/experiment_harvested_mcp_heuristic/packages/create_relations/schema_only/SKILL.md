# create_relations

**Condition:** `schema_only`

## Summary
Create multiple new relations between entities in the knowledge graph. Relations should be in active voice

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for create_relations
```json
{
  "relations": [
    {}
  ]
}
```
