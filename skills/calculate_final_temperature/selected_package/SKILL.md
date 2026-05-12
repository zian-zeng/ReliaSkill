# calculate_final_temperature

**Condition:** `multi_candidate_skill`

## Summary
Calculate the final temperature when different quantities of the same gas at different temperatures are mixed. Provide all required fields: `quantity1`, `temperature1`, `quantity2`, and `temperature2`.

## When to use
- Use `calculate_final_temperature` when the user's request directly matches this tool's purpose.
- Provide all required fields: `quantity1`, `temperature1`, `quantity2`, and `temperature2`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `quantity1`, integer, required: The quantity of the first sample of gas.
- `temperature1`, integer, required: The temperature of the first sample of gas.
- `quantity2`, integer, required: The quantity of the second sample of gas.
- `temperature2`, integer, required: The temperature of the second sample of gas.

## Argument template
```json
{
  "quantity1": 1,
  "temperature1": 1,
  "quantity2": 1,
  "temperature2": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_final_temperature
```json
{
  "quantity1": 1,
  "temperature1": 1,
  "quantity2": 1,
  "temperature2": 1
}
```
- Richer invocation that uses optional controls for calculate_final_temperature
```json
{
  "quantity1": 2,
  "temperature1": 2,
  "quantity2": 2,
  "temperature2": 2
}
```
