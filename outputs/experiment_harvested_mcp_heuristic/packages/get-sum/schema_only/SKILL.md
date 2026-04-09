# get-sum

**Condition:** `schema_only`

## Summary
Returns the sum of two numbers

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for get-sum
```json
{
  "a": 1.0,
  "b": 1.0
}
```
- Schema-aligned full call for get-sum
```json
{
  "a": 2.0,
  "b": 2.0
}
```
