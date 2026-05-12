# calculate_area

**Condition:** `multi_candidate_skill`

## Summary
Calculate the area of a right-angled triangle given the lengths of its base and height. Provide all required fields: `base`, and `height`.

## When to use
- Use `calculate_area` when the user's request directly matches this tool's purpose.
- Provide all required fields: `base`, and `height`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `base`, integer, required: The length of the base of the right-angled triangle.
- `height`, integer, required: The height of the right-angled triangle.
- `unit`, string, optional: The unit of measure used. Defaults to 'cm'.

## Argument template
```json
{
  "base": 1,
  "height": 1,
  "unit": "sample_unit_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_area
```json
{
  "base": 1,
  "height": 1
}
```
- Richer invocation that uses optional controls for calculate_area
```json
{
  "base": 2,
  "height": 2,
  "unit": "sample_unit_2"
}
```
