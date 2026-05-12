# calculate_circumference

**Condition:** `multi_candidate_skill`

## Summary
Calculates the circumference of a circle with a given radius. Provide the required field `radius`.

## When to use
- Use `calculate_circumference` when the user's request directly matches this tool's purpose.
- Provide the required field `radius`.
- Optional control is available through `unit` when the request needs extra specificity.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `radius`, integer, required: The radius of the circle in the unit given.
- `unit`, string, optional: The unit of measurement for the radius. Default is 'cm'.

## Argument template
```json
{
  "radius": 4,
  "unit": "sample_unit_4"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_circumference
```json
{
  "radius": 1
}
```
- Richer invocation that uses optional controls for calculate_circumference
```json
{
  "radius": 2,
  "unit": "sample_unit_2"
}
```
- Required-argument dev behavior example.
```json
{
  "radius": 3
}
```
- Optional, enum, nested, or array argument example.
```json
{
  "radius": 4,
  "unit": "sample_unit_4"
}
```
