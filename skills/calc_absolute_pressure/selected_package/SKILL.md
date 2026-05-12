# calc_absolute_pressure

**Condition:** `multi_candidate_skill`

## Summary
Calculates the absolute pressure from gauge and atmospheric pressures. Provide the required field `gauge_pressure`.

## When to use
- Use `calc_absolute_pressure` when the user's request directly matches this tool's purpose.
- Provide the required field `gauge_pressure`.
- Optional control is available through `atm_pressure` when the request needs extra specificity.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `atm_pressure`, float, optional: The atmospheric pressure in atmospheres (atm). Default is 1 atm if not provided.
- `gauge_pressure`, float, required: The gauge pressure in atmospheres (atm). Must be provided.

## Argument template
```json
{
  "atm_pressure": null,
  "gauge_pressure": null
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calc_absolute_pressure
```json
{
  "gauge_pressure": null
}
```
- Richer invocation that uses optional controls for calc_absolute_pressure
```json
{
  "atm_pressure": null,
  "gauge_pressure": null
}
```
- Required-argument dev behavior example.
```json
{
  "gauge_pressure": null
}
```
- Optional, enum, nested, or array argument example.
```json
{
  "atm_pressure": null,
  "gauge_pressure": null
}
```
