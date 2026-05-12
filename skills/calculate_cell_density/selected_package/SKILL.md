# calculate_cell_density

**Condition:** `multi_candidate_skill`

## Summary
Calculate the cell density of a biological sample based on its optical density and the experiment dilution. Provide all required fields: `optical_density`, and `dilution`.

## When to use
- Use `calculate_cell_density` when the user's request directly matches this tool's purpose.
- Provide all required fields: `optical_density`, and `dilution`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `optical_density`, float, required: The optical density of the sample, usually obtained from a spectrophotometer reading.
- `dilution`, integer, required: The dilution factor applied during the experiment.
- `calibration_factor`, float, optional: The calibration factor to adjust the density, default value is 1e9 assuming cell density is in CFU/mL.

## Argument template
```json
{
  "optical_density": null,
  "dilution": 1,
  "calibration_factor": null
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_cell_density
```json
{
  "optical_density": null,
  "dilution": 1
}
```
- Richer invocation that uses optional controls for calculate_cell_density
```json
{
  "optical_density": null,
  "dilution": 2,
  "calibration_factor": null
}
```
