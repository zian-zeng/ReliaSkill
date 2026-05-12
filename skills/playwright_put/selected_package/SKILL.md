# playwright_put

**Condition:** `multi_candidate_skill`

## Summary
Perform an HTTP PUT request. Provide all required fields: `url`, and `value`.

## When to use
- Use `playwright_put` when the user's request directly matches this tool's purpose.
- Provide all required fields: `url`, and `value`.
- Use only when the request clearly needs `playwright_put`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use for adjacent tools with similar names, descriptions, or arguments.
- Do not use for read/write, search/fetch, create/update, delete/preview, or execute/explain mismatches.
- If the request lacks required fields, abstain or ask for clarification.

## Arguments
- `url`, string, required: URL to perform PUT operation
- `value`, string, required: Data to PUT in the body

## Argument template
```json
{
  "url": "https://example.com/resource",
  "value": "sample_value_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for playwright_put
```json
{
  "url": "https://example.com/resource",
  "value": "sample_value_1"
}
```
- Richer invocation that uses optional controls for playwright_put
```json
{
  "url": "https://example.com/resource",
  "value": "sample_value_2"
}
```
