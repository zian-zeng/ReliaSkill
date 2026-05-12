# calculate_final_velocity

**Condition:** `multi_candidate_skill`

## Summary
Calculate the final velocity of an object under constant acceleration, knowing its initial velocity, acceleration, and time of acceleration. Provide all required fields: `initial_velocity`, `acceleration`, and `time`.

## When to use
- Use `calculate_final_velocity` when the user's request directly matches this tool's purpose.
- Provide all required fields: `initial_velocity`, `acceleration`, and `time`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `initial_velocity`, integer, required: The initial velocity of the object.
- `acceleration`, float, required: The acceleration of the object.
- `time`, integer, required: The time of acceleration.

## Argument template
```json
{
  "initial_velocity": 1,
  "acceleration": null,
  "time": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_final_velocity
```json
{
  "initial_velocity": 1,
  "acceleration": null,
  "time": 1
}
```
- Richer invocation that uses optional controls for calculate_final_velocity
```json
{
  "initial_velocity": 2,
  "acceleration": null,
  "time": 2
}
```
