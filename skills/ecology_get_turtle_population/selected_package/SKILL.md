# ecology.get_turtle_population

**Condition:** `multi_candidate_skill`

## Summary
Get the population and species of turtles in a specific location. Provide the required field `location`.

## When to use
- Use `ecology.get_turtle_population` when the user's request directly matches this tool's purpose.
- Provide the required field `location`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `location`, string, required: The name of the location.
- `year`, integer, optional: The year of the data requested. (optional) Default is 2024.
- `species`, boolean, optional: Whether to include species information. Default is false. (optional)

## Argument template
```json
{
  "location": "sample_location_1",
  "year": 1,
  "species": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for ecology.get_turtle_population
```json
{
  "location": "sample_location_1"
}
```
- Richer invocation that uses optional controls for ecology.get_turtle_population
```json
{
  "location": "sample_location_2",
  "year": 2,
  "species": true
}
```
