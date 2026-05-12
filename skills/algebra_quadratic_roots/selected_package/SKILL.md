# algebra.quadratic_roots

**Condition:** `multi_candidate_skill`

## Summary
Find the roots of a quadratic equation ax^2 + bx + c = 0. Provide all required fields: `a`, `b`, and `c`.

## When to use
- Use `algebra.quadratic_roots` when the user's request directly matches this tool's purpose.
- Provide all required fields: `a`, `b`, and `c`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `a`, integer, required: Coefficient of x^2.
- `b`, integer, required: Coefficient of x.
- `c`, integer, required: Constant term.

## Argument template
```json
{
  "a": 1,
  "b": 1,
  "c": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for algebra.quadratic_roots
```json
{
  "a": 1,
  "b": 1,
  "c": 1
}
```
- Richer invocation that uses optional controls for algebra.quadratic_roots
```json
{
  "a": 2,
  "b": 2,
  "c": 2
}
```
