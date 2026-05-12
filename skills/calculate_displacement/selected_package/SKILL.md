# calculate_displacement

**Condition:** `multi_candidate_skill`

## Summary
Calculates the displacement of an object in motion given initial velocity, time, and acceleration. Provide all required fields: `initial_velocity`, and `time`.

## When to use
- Use `calculate_displacement` when the user's request directly matches this tool's purpose.
- Provide all required fields: `initial_velocity`, and `time`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `initial_velocity`, float, required: The initial velocity of the object in m/s.
- `time`, float, required: The time in seconds that the object has been in motion.
- `acceleration`, float, optional, default=0: The acceleration of the object in m/s^2.

## Argument template
```json
{
  "initial_velocity": null,
  "time": null,
  "acceleration": 0
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_displacement
```json
{
  "initial_velocity": null,
  "time": null
}
```
- Richer invocation that uses optional controls for calculate_displacement
```json
{
  "initial_velocity": null,
  "time": null,
  "acceleration": 0
}
```
