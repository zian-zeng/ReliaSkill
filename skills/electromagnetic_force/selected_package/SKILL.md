# electromagnetic_force

**Condition:** `multi_candidate_skill`

## Summary
Calculate the electromagnetic force between two charges placed at a certain distance. Provide all required fields: `charge1`, `charge2`, and `distance`.

## When to use
- Use `electromagnetic_force` when the user's request directly matches this tool's purpose.
- Provide all required fields: `charge1`, `charge2`, and `distance`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `charge1`, float, required: The magnitude of the first charge in coulombs.
- `charge2`, float, required: The magnitude of the second charge in coulombs.
- `distance`, float, required: The distance between the two charges in meters.
- `medium_permittivity`, float, optional: The relative permittivity of the medium in which the charges are present. Default is 8.854 x 10^-12 F/m (vacuum permittivity).

## Argument template
```json
{
  "charge1": null,
  "charge2": null,
  "distance": null,
  "medium_permittivity": null
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for electromagnetic_force
```json
{
  "charge1": null,
  "charge2": null,
  "distance": null
}
```
- Richer invocation that uses optional controls for electromagnetic_force
```json
{
  "charge1": null,
  "charge2": null,
  "distance": null,
  "medium_permittivity": null
}
```
