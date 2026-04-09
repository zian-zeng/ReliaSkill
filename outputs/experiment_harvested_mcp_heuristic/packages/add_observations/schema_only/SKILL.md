# add_observations

**Condition:** `schema_only`

## Summary
Add new observations to existing entities in the knowledge graph

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

## Arguments
- `observations`, array, required: No description provided.

## Argument template
```json
{
  "observations": [
    {}
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid call for add_observations
```json
{
  "observations": [
    {}
  ]
}
```
