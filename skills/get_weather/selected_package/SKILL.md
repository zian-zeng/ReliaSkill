# get_weather

**Condition:** `multi_candidate_skill`

## Summary
Fetch the current weather for a given city. Provide all required fields: `city`, and `unit`.

## When to use
- Use `get_weather` when the user's request directly matches this tool's purpose.
- Provide all required fields: `city`, and `unit`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `unit`: 'C', 'F'.
- Do not use when required inputs are missing.

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
- Minimal valid request that satisfies the required fields for get_weather
```json
{
  "city": "New York",
  "unit": "C"
}
```
- Richer invocation that uses optional controls for get_weather
```json
{
  "city": "New York",
  "unit": "F",
  "include_forecast": false
}
```
