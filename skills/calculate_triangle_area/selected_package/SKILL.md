# calculate_triangle_area

**Condition:** `multi_candidate_skill`

## Summary
Calculate the area of a triangle given its base and height. Provide all required fields: `base`, and `height`.

## When to use
- Use `calculate_triangle_area` when the user's request directly matches this tool's purpose.
- Provide all required fields: `base`, and `height`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `base`, float, required: The base of the triangle.
- `height`, float, required: The height of the triangle.
- `unit`, string, optional: The unit of measure (defaults to 'units' if not specified)

## Argument template
```json
{
  "base": null,
  "height": null,
  "unit": "sample_unit_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_triangle_area
```json
{
  "base": null,
  "height": null
}
```
- Richer invocation that uses optional controls for calculate_triangle_area
```json
{
  "base": null,
  "height": null,
  "unit": "sample_unit_2"
}
```
