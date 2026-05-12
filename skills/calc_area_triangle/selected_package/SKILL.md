# calc_area_triangle

**Condition:** `multi_candidate_skill`

## Summary
Calculate the area of a triangle with the formula area = 0.5 * base * height. Provide all required fields: `base`, and `height`.

## When to use
- Use `calc_area_triangle` when the user's request directly matches this tool's purpose.
- Provide all required fields: `base`, and `height`.
- Use only when the request clearly needs `calc_area_triangle`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use for adjacent tools with similar names, descriptions, or arguments.
- Do not use for read/write, search/fetch, create/update, delete/preview, or execute/explain mismatches.
- If the request lacks required fields, abstain or ask for clarification.

## Arguments
- `base`, integer, required: The length of the base of the triangle in meters.
- `height`, integer, required: The perpendicular height of the triangle from the base to the opposite vertex in meters.

## Argument template
```json
{
  "base": 1,
  "height": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calc_area_triangle
```json
{
  "base": 1,
  "height": 1
}
```
- Richer invocation that uses optional controls for calc_area_triangle
```json
{
  "base": 2,
  "height": 2
}
```
