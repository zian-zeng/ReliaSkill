# get_weather

**Condition:** `autoskill_base`

## Summary
Fetch the current weather for a given city. Provide all required fields: `city`, and `unit`.

## When to use
- Use `get_weather` when the user's request directly matches this tool's purpose.
- Provide all required fields: `city`, and `unit`.
- Optional control is available through `include_forecast` when the request needs extra specificity.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `unit`: 'C', 'F'.
- Do not let semantic cues override explicit user-provided field values.

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
```json
{
  "unit": {
    "c": "C",
    "f": "F",
    "fahrenheit": "F",
    "celsius": "C",
    "centigrade": "C"
  }
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
