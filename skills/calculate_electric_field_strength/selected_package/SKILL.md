# calculate_electric_field_strength

**Condition:** `multi_candidate_skill`

## Summary
Calculate the electric field strength at a certain distance from a point charge. Provide all required fields: `charge`, and `distance`.

## When to use
- Use `calculate_electric_field_strength` when the user's request directly matches this tool's purpose.
- Provide all required fields: `charge`, and `distance`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `charge`, float, required: The charge in Coulombs.
- `distance`, integer, required: The distance from the charge in meters.
- `medium`, string, optional: The medium in which the charge and the point of calculation is located. Default is 'vacuum'.

## Argument template
```json
{
  "charge": null,
  "distance": 1,
  "medium": "sample_medium_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_electric_field_strength
```json
{
  "charge": null,
  "distance": 1
}
```
- Richer invocation that uses optional controls for calculate_electric_field_strength
```json
{
  "charge": null,
  "distance": 2,
  "medium": "sample_medium_2"
}
```
