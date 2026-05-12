# calculate_average

**Condition:** `multi_candidate_skill`

## Summary
This function calculates the average grade across different subjects for a specific student. Provide the required field `gradeDict`.

## When to use
- Use `calculate_average` when the user's request directly matches this tool's purpose.
- Provide the required field `gradeDict`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `gradeDict`, dict, required: A dictionary where keys represent subjects and values represent scores

## Argument template
```json
{
  "gradeDict": null
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_average
```json
{
  "gradeDict": null
}
```
- Richer invocation that uses optional controls for calculate_average
```json
{
  "gradeDict": null
}
```
- Required-argument dev behavior example.
```json
{
  "gradeDict": null
}
```
