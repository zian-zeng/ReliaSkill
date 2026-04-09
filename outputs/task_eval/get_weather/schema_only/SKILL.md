# get_weather

**Condition:** `schema_only`

## Summary
Fetch the current weather for a given city.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

## Arguments
- `city`, string, required: City name to query.
- `unit`, string, required, enum=['C', 'F']: Temperature unit.
- `include_forecast`, boolean, optional, default=False: Whether to include a short forecast.

## Argument template
```json
{
  "city": "New York",
  "unit": "C",
  "include_forecast": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid call for get_weather
```json
{
  "city": "New York",
  "unit": "C"
}
```
- Schema-aligned full call for get_weather
```json
{
  "city": "New York",
  "unit": "F",
  "include_forecast": false
}
```
