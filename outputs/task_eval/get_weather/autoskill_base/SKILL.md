# get_weather

**Condition:** `autoskill_base`

## Summary
Fetch the current weather for a given city. Provide all required fields: `city`, and `unit`.

## When to use
- Use `get_weather` when the user's request directly matches this tool's purpose.
- Provide all required fields: `city`, and `unit`.
- Optional control is available through `include_forecast` when the request needs extra specificity.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `unit`: 'C', 'F'.

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
