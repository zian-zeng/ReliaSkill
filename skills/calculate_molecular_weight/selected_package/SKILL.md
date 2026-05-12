# calculate_molecular_weight

**Condition:** `multi_candidate_skill`

## Summary
Calculate the molecular weight of a compound given the compound formula. Provide all required fields: `compound`, and `to_unit`.

## When to use
- Use `calculate_molecular_weight` when the user's request directly matches this tool's purpose.
- Provide all required fields: `compound`, and `to_unit`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `compound`, string, required: The molecular formula of the compound.
- `to_unit`, string, required: The unit in which to return the result.

## Argument template
```json
{
  "compound": "sample_compound_1",
  "to_unit": "sample_to_unit_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_molecular_weight
```json
{
  "compound": "sample_compound_1",
  "to_unit": "sample_to_unit_1"
}
```
- Richer invocation that uses optional controls for calculate_molecular_weight
```json
{
  "compound": "sample_compound_2",
  "to_unit": "sample_to_unit_2"
}
```
