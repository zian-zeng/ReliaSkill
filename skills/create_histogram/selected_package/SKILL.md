# create_histogram

**Condition:** `multi_candidate_skill`

## Summary
Create a histogram based on provided data. Provide all required fields: `data`, and `bins`.

## When to use
- Use `create_histogram` when the user's request directly matches this tool's purpose.
- Provide all required fields: `data`, and `bins`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `data`, array, required: The data for which histogram needs to be plotted.
- `bins`, integer, required: The number of equal-width bins in the range. Default is 10.

## Argument template
```json
{
  "data": [
    null
  ],
  "bins": 4
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for create_histogram
```json
{
  "data": [
    null
  ],
  "bins": 1
}
```
- Richer invocation that uses optional controls for create_histogram
```json
{
  "data": [
    null
  ],
  "bins": 2
}
```
- Required-argument dev behavior example.
```json
{
  "data": [
    null
  ],
  "bins": 3
}
```
- Optional, enum, nested, or array argument example.
```json
{
  "data": [
    null
  ],
  "bins": 4
}
```
