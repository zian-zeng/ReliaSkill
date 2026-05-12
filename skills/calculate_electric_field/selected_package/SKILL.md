# calculate_electric_field

**Condition:** `multi_candidate_skill`

## Summary
Calculate the electric field produced by a charge at a certain distance. Provide all required fields: `charge`, and `distance`.

## When to use
- Use `calculate_electric_field` when the user's request directly matches this tool's purpose.
- Provide all required fields: `charge`, and `distance`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `charge`, float, required: Charge in coulombs producing the electric field.
- `distance`, float, required: Distance from the charge in meters where the field is being measured.
- `permitivity`, float, optional: Permitivity of the space where field is being calculated, default is for vacuum.

## Argument template
```json
{
  "charge": null,
  "distance": null,
  "permitivity": null
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_electric_field
```json
{
  "charge": null,
  "distance": null
}
```
- Richer invocation that uses optional controls for calculate_electric_field
```json
{
  "charge": null,
  "distance": null,
  "permitivity": null
}
```
