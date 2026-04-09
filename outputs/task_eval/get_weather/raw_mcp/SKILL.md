# get_weather

**Condition:** `raw_mcp`

## Summary
Fetch the current weather for a given city.

## When to use
- Use the original MCP description and schema directly without added guidance.
- Consult schema.normalized.json for the exact argument contract.

## When not to use
- Do not assume example calls or usage heuristics beyond the original schema.

## Arguments
- `city`, string, required: City name to query.
- `unit`, string, required, enum=['C', 'F']: Temperature unit.
- `include_forecast`, boolean, optional, default=False: Whether to include a short forecast.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Semantic hints
No explicit semantic hints for this condition.

## Examples
No synthesized examples for this condition.
