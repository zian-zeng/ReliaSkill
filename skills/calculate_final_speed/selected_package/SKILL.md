# calculate_final_speed

**Condition:** `multi_candidate_skill`

## Summary
Calculate the final speed of an object dropped from a certain height without air resistance. Provide all required fields: `initial_velocity`, and `height`.

## When to use
- Use `calculate_final_speed` when the user's request directly matches this tool's purpose.
- Provide all required fields: `initial_velocity`, and `height`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `initial_velocity`, integer, required: The initial velocity of the object.
- `height`, integer, required: The height from which the object is dropped.
- `gravity`, float, optional: The gravitational acceleration. Default is 9.8 m/s^2.

## Argument template
```json
{
  "initial_velocity": 1,
  "height": 1,
  "gravity": null
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_final_speed
```json
{
  "initial_velocity": 1,
  "height": 1
}
```
- Richer invocation that uses optional controls for calculate_final_speed
```json
{
  "initial_velocity": 2,
  "height": 2,
  "gravity": null
}
```
