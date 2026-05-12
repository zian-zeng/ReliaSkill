# average_temperature

**Condition:** `multi_candidate_skill`

## Summary
Retrieves the average temperature for a specific location over the defined timeframe. Provide all required fields: `location`, and `days`.

## When to use
- Use `average_temperature` when the user's request directly matches this tool's purpose.
- Provide all required fields: `location`, and `days`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `location`, string, required: The city to get the average temperature for. It should format as city name such as Boston.
- `days`, integer, required: The number of days to get the average temperature for.
- `temp_unit`, string, optional: The temperature unit ('Celsius' or 'Fahrenheit'). Default is 'Fahrenheit'.

## Argument template
```json
{
  "location": "sample_location_1",
  "days": 1,
  "temp_unit": "sample_temp_unit_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for average_temperature
```json
{
  "location": "sample_location_1",
  "days": 1
}
```
- Richer invocation that uses optional controls for average_temperature
```json
{
  "location": "sample_location_2",
  "days": 2,
  "temp_unit": "sample_temp_unit_2"
}
```
