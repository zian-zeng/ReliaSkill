# city_distance.find_shortest

**Condition:** `multi_candidate_skill`

## Summary
Calculates the shortest distance between two cities via available public transportation. Provide all required fields: `start_city`, and `end_city`.

## When to use
- Use `city_distance.find_shortest` when the user's request directly matches this tool's purpose.
- Provide all required fields: `start_city`, and `end_city`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `start_city`, string, required: The city you are starting from. The parameter is in the format of city name.
- `end_city`, string, required: The city you are heading to.The parameter is in the format of city name.
- `transportation`, string, optional: Preferred mode of public transportation. Default is 'bus'.
- `allow_transfer`, boolean, optional: Allows transfer between different transportation if true. Default is false.

## Argument template
```json
{
  "start_city": "New York",
  "end_city": "New York",
  "transportation": "sample_transportation_1",
  "allow_transfer": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for city_distance.find_shortest
```json
{
  "start_city": "New York",
  "end_city": "New York"
}
```
- Richer invocation that uses optional controls for city_distance.find_shortest
```json
{
  "start_city": "New York",
  "end_city": "New York",
  "transportation": "sample_transportation_2",
  "allow_transfer": true
}
```
