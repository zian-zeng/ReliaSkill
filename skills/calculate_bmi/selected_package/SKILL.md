# calculate_bmi

**Condition:** `multi_candidate_skill`

## Summary
Calculate the Body Mass Index (BMI) for a person based on their weight and height. Provide all required fields: `weight`, and `height`.

## When to use
- Use `calculate_bmi` when the user's request directly matches this tool's purpose.
- Provide all required fields: `weight`, and `height`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `weight`, integer, required: The weight of the person in kilograms.
- `height`, integer, required: The height of the person in centimeters.
- `system`, string, optional: The system of units to be used, 'metric' or 'imperial'. Default is 'metric'.

## Argument template
```json
{
  "weight": 1,
  "height": 1,
  "system": "sample_system_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_bmi
```json
{
  "weight": 1,
  "height": 1
}
```
- Richer invocation that uses optional controls for calculate_bmi
```json
{
  "weight": 2,
  "height": 2,
  "system": "sample_system_2"
}
```
