# calculate_derivative

**Condition:** `multi_candidate_skill`

## Summary
Calculate the derivative of a single-variable function. Provide all required fields: `func`, and `x_value`.

## When to use
- Use `calculate_derivative` when the user's request directly matches this tool's purpose.
- Provide all required fields: `func`, and `x_value`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `func`, string, required: The function to be differentiated.
- `x_value`, integer, required: The x-value at which the derivative should be calculated.
- `order`, integer, optional, default=1: The order of the derivative (optional). Default is 1st order.

## Argument template
```json
{
  "func": "sample_func_1",
  "x_value": 1,
  "order": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_derivative
```json
{
  "func": "sample_func_1",
  "x_value": 1
}
```
- Richer invocation that uses optional controls for calculate_derivative
```json
{
  "func": "sample_func_2",
  "x_value": 2,
  "order": 1
}
```
