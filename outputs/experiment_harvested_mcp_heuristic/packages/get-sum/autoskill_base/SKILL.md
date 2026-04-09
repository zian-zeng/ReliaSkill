# get-sum

**Condition:** `autoskill_base`

## Summary
Returns the sum of two numbers. Provide all required fields: `a`, and `b`.

## When to use
- Use `get-sum` when the user's request directly matches this tool's purpose.
- Provide all required fields: `a`, and `b`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
