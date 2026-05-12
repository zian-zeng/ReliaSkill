# calculate_magnetic_field_strength

**Condition:** `multi_candidate_skill`

## Summary
Calculate the magnetic field strength at a point a certain distance away from a long wire carrying a current. Provide all required fields: `current`, and `distance`.

## When to use
- Use `calculate_magnetic_field_strength` when the user's request directly matches this tool's purpose.
- Provide all required fields: `current`, and `distance`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `current`, integer, required: The current flowing through the wire in Amperes.
- `distance`, integer, required: The perpendicular distance from the wire to the point where the magnetic field is being calculated.
- `permeability`, float, optional: The permeability of the medium. Default is 12.57e-7 (Vacuum Permeability).

## Argument template
```json
{
  "current": 1,
  "distance": 1,
  "permeability": null
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_magnetic_field_strength
```json
{
  "current": 1,
  "distance": 1
}
```
- Richer invocation that uses optional controls for calculate_magnetic_field_strength
```json
{
  "current": 2,
  "distance": 2,
  "permeability": null
}
```
