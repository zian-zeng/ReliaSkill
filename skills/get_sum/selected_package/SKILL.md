# get-sum

**Condition:** `multi_candidate_skill`

## Summary
Returns the sum of two numbers. Provide all required fields: `a`, and `b`.

## When to use
- Use `get-sum` when the user's request directly matches this tool's purpose.
- Provide all required fields: `a`, and `b`.
- Use only when the request clearly needs `get-sum`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use for adjacent tools with similar names, descriptions, or arguments.
- Do not use for read/write, search/fetch, create/update, delete/preview, or execute/explain mismatches.
- If the request lacks required fields, abstain or ask for clarification.

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
- Minimal valid request that satisfies the required fields for get-sum
```json
{
  "a": 1.0,
  "b": 1.0
}
```
- Richer invocation that uses optional controls for get-sum
```json
{
  "a": 2.0,
  "b": 2.0
}
```
