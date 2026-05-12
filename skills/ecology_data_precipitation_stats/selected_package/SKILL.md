# ecology_data.precipitation_stats

**Condition:** `multi_candidate_skill`

## Summary
Retrieve precipitation data for a specified location and time period. Provide all required fields: `location`, and `time_frame`.

## When to use
- Use `ecology_data.precipitation_stats` when the user's request directly matches this tool's purpose.
- Provide all required fields: `location`, and `time_frame`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `time_frame`: 'six_months', 'year', 'five_years'.
- Do not use when required inputs are missing.

## Arguments
- `location`, string, required: The name of the location, e.g., 'Amazon rainforest'.
- `time_frame`, string, required, enum=['six_months', 'year', 'five_years']: The time period for which data is required.

## Argument template
```json
{
  "location": "sample_location_1",
  "time_frame": "six_months"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for ecology_data.precipitation_stats
```json
{
  "location": "sample_location_1",
  "time_frame": "six_months"
}
```
- Richer invocation that uses optional controls for ecology_data.precipitation_stats
```json
{
  "location": "sample_location_2",
  "time_frame": "year"
}
```
