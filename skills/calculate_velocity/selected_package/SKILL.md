# calculate_velocity

**Condition:** `multi_candidate_skill`

## Summary
Calculate the velocity for a certain distance travelled within a specific duration. Provide all required fields: `distance`, and `duration`.

## When to use
- Use `calculate_velocity` when the user's request directly matches this tool's purpose.
- Provide all required fields: `distance`, and `duration`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `distance`, integer, required: The distance travelled by the object, typically in kilometers.
- `duration`, integer, required: The duration of the journey, typically in hours.
- `unit`, string, optional: Optional parameter. The unit to return the velocity in. If not provided, the default is km/h.

## Argument template
```json
{
  "distance": 1,
  "duration": 1,
  "unit": "sample_unit_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_velocity
```json
{
  "distance": 1,
  "duration": 1
}
```
- Richer invocation that uses optional controls for calculate_velocity
```json
{
  "distance": 2,
  "duration": 2,
  "unit": "sample_unit_2"
}
```
