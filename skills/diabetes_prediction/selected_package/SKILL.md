# diabetes_prediction

**Condition:** `multi_candidate_skill`

## Summary
Predict the likelihood of diabetes type 2 based on a person's weight and height. Provide all required fields: `weight`, `height`, and `activity_level`.

## When to use
- Use `diabetes_prediction` when the user's request directly matches this tool's purpose.
- Provide all required fields: `weight`, `height`, and `activity_level`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `activity_level`: 'sedentary', 'lightly active', 'moderately active', 'very active'.
- Do not use when required inputs are missing.

## Arguments
- `weight`, float, required: Weight of the person in lbs.
- `height`, float, required: Height of the person in inches.
- `activity_level`, string, required, enum=['sedentary', 'lightly active', 'moderately active', 'very active', 'extra active']: Physical activity level of the person.

## Argument template
```json
{
  "weight": null,
  "height": null,
  "activity_level": "sedentary"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for diabetes_prediction
```json
{
  "weight": null,
  "height": null,
  "activity_level": "sedentary"
}
```
- Richer invocation that uses optional controls for diabetes_prediction
```json
{
  "weight": null,
  "height": null,
  "activity_level": "lightly active"
}
```
