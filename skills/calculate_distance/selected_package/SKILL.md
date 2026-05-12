# calculate_distance

**Condition:** `multi_candidate_skill`

## Summary
Calculate distance between two locations. Provide all required fields: `start_point`, and `end_point`.

## When to use
- Use `calculate_distance` when the user's request directly matches this tool's purpose.
- Provide all required fields: `start_point`, and `end_point`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `start_point`, string, required: Starting point of the journey.
- `end_point`, string, required: Ending point of the journey.

## Argument template
```json
{
  "start_point": "sample_start_point_1",
  "end_point": "sample_end_point_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_distance
```json
{
  "start_point": "sample_start_point_1",
  "end_point": "sample_end_point_1"
}
```
- Richer invocation that uses optional controls for calculate_distance
```json
{
  "start_point": "sample_start_point_2",
  "end_point": "sample_end_point_2"
}
```
