# calculate_resonant_frequency

**Condition:** `multi_candidate_skill`

## Summary
Calculate the resonant frequency of an LC (inductor-capacitor) circuit. Provide all required fields: `inductance`, and `capacitance`.

## When to use
- Use `calculate_resonant_frequency` when the user's request directly matches this tool's purpose.
- Provide all required fields: `inductance`, and `capacitance`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `inductance`, float, required: The inductance (L) in henries (H).
- `capacitance`, float, required: The capacitance (C) in farads (F).
- `round_off`, integer, optional: Rounding off the result to a certain decimal places, default is 2.

## Argument template
```json
{
  "inductance": null,
  "capacitance": null,
  "round_off": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_resonant_frequency
```json
{
  "inductance": null,
  "capacitance": null
}
```
- Richer invocation that uses optional controls for calculate_resonant_frequency
```json
{
  "inductance": null,
  "capacitance": null,
  "round_off": 2
}
```
