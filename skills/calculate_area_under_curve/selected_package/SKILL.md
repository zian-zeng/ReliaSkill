# calculate_area_under_curve

**Condition:** `multi_candidate_skill`

## Summary
Calculate the area under a mathematical function within a given interval. Provide all required fields: `function`, and `interval`.

## When to use
- Use `calculate_area_under_curve` when the user's request directly matches this tool's purpose.
- Provide all required fields: `function`, and `interval`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `function`, string, required: The mathematical function as a string.
- `interval`, array, required: An array that defines the interval to calculate the area under the curve from the start to the end point.
- `method`, string, optional: The numerical method to approximate the area under the curve. The default value is 'trapezoidal'.

## Argument template
```json
{
  "function": "sample_function_1",
  "interval": [
    null
  ],
  "method": "sample_method_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_area_under_curve
```json
{
  "function": "sample_function_1",
  "interval": [
    null
  ]
}
```
- Richer invocation that uses optional controls for calculate_area_under_curve
```json
{
  "function": "sample_function_2",
  "interval": [
    null
  ],
  "method": "sample_method_2"
}
```
