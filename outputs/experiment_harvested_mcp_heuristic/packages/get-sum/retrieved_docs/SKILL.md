# get-sum

**Condition:** `retrieved_docs`

## Summary
Returns the sum of two numbers Get Sum Tool

## When to use
- Returns the sum of two numbers
- Get Sum Tool
- a required
- b required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

## Arguments
- `a`, number, required: No description provided.
- `b`, number, required: No description provided.

## Argument template
```json
{
  "a": 1.0,
  "b": 1.0
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Retrieved-docs minimal call for get-sum
```json
{
  "a": 1.0,
  "b": 1.0
}
```
- Retrieved-docs fuller call for get-sum
```json
{
  "a": 2.0,
  "b": 2.0
}
```
