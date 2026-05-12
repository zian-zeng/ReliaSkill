# calculate_magnetic_field

**Condition:** `multi_candidate_skill`

## Summary
Calculate the magnetic field produced at the center of a circular loop carrying current. Provide all required fields: `current`, and `radius`.

## When to use
- Use `calculate_magnetic_field` when the user's request directly matches this tool's purpose.
- Provide all required fields: `current`, and `radius`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `current`, integer, required: The current through the circular loop in Amperes.
- `radius`, integer, required: The radius of the circular loop in meters.
- `permeability`, float, optional: The magnetic permeability. Default is permeability in free space, 0.01

## Argument template
```json
{
  "current": 1,
  "radius": 1,
  "permeability": null
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_magnetic_field
```json
{
  "current": 1,
  "radius": 1
}
```
- Richer invocation that uses optional controls for calculate_magnetic_field
```json
{
  "current": 2,
  "radius": 2,
  "permeability": null
}
```
