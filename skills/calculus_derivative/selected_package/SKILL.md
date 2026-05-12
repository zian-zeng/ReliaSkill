# calculus.derivative

**Condition:** `multi_candidate_skill`

## Summary
Compute the derivative of a function at a specific value. Provide all required fields: `function`, and `value`.

## When to use
- Use `calculus.derivative` when the user's request directly matches this tool's purpose.
- Provide all required fields: `function`, and `value`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `function`, string, required: The function to calculate the derivative of.
- `value`, integer, required: The value where the derivative needs to be calculated at.
- `function_variable`, string, optional: The variable present in the function, for instance x or y, etc. Default is 'x'

## Argument template
```json
{
  "function": "sample_function_1",
  "value": 1,
  "function_variable": "sample_function_variable_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculus.derivative
```json
{
  "function": "sample_function_1",
  "value": 1
}
```
- Richer invocation that uses optional controls for calculus.derivative
```json
{
  "function": "sample_function_2",
  "value": 2,
  "function_variable": "sample_function_variable_2"
}
```
