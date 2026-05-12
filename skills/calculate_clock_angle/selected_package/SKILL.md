# calculate_clock_angle

**Condition:** `multi_candidate_skill`

## Summary
Calculate the angle between the hour and minute hands of a clock at a given time. Provide all required fields: `hours`, and `minutes`.

## When to use
- Use `calculate_clock_angle` when the user's request directly matches this tool's purpose.
- Provide all required fields: `hours`, and `minutes`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `hours`, integer, required: The hour on the clock face.
- `minutes`, integer, required: The minutes on the clock face.
- `round_to`, integer, optional: The number of decimal places to round the result to, default is 2.

## Argument template
```json
{
  "hours": 1,
  "minutes": 1,
  "round_to": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_clock_angle
```json
{
  "hours": 1,
  "minutes": 1
}
```
- Richer invocation that uses optional controls for calculate_clock_angle
```json
{
  "hours": 2,
  "minutes": 2,
  "round_to": 2
}
```
