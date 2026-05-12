# calculate_electrostatic_potential

**Condition:** `multi_candidate_skill`

## Summary
Calculate the electrostatic potential between two charged bodies using the principle of Coulomb's Law. Provide all required fields: `charge1`, `charge2`, and `distance`.

## When to use
- Use `calculate_electrostatic_potential` when the user's request directly matches this tool's purpose.
- Provide all required fields: `charge1`, `charge2`, and `distance`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `charge1`, float, required: The quantity of charge on the first body.
- `charge2`, float, required: The quantity of charge on the second body.
- `distance`, float, required: The distance between the two bodies.
- `constant`, float, optional: The value of the electrostatic constant. Default is 898755178.73

## Argument template
```json
{
  "charge1": null,
  "charge2": null,
  "distance": null,
  "constant": null
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_electrostatic_potential
```json
{
  "charge1": null,
  "charge2": null,
  "distance": null
}
```
- Richer invocation that uses optional controls for calculate_electrostatic_potential
```json
{
  "charge1": null,
  "charge2": null,
  "distance": null,
  "constant": null
}
```
