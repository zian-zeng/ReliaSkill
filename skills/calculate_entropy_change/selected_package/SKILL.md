# calculate_entropy_change

**Condition:** `multi_candidate_skill`

## Summary
Calculate the entropy change for an isothermal and reversible process. Provide all required fields: `initial_temp`, `final_temp`, and `heat_capacity`.

## When to use
- Use `calculate_entropy_change` when the user's request directly matches this tool's purpose.
- Provide all required fields: `initial_temp`, `final_temp`, and `heat_capacity`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `initial_temp`, float, required: The initial temperature in Kelvin.
- `final_temp`, float, required: The final temperature in Kelvin.
- `heat_capacity`, float, required: The heat capacity in J/K.
- `isothermal`, boolean, optional: Whether the process is isothermal. Default is True.

## Argument template
```json
{
  "initial_temp": null,
  "final_temp": null,
  "heat_capacity": null,
  "isothermal": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_entropy_change
```json
{
  "initial_temp": null,
  "final_temp": null,
  "heat_capacity": null
}
```
- Richer invocation that uses optional controls for calculate_entropy_change
```json
{
  "initial_temp": null,
  "final_temp": null,
  "heat_capacity": null,
  "isothermal": true
}
```
