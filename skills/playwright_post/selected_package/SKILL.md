# playwright_post

**Condition:** `multi_candidate_skill`

## Summary
Perform an HTTP POST request. Provide all required fields: `url`, and `value`.

## When to use
- Use `playwright_post` when the user's request directly matches this tool's purpose.
- Provide all required fields: `url`, and `value`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `url`, string, required: URL to perform POST operation
- `value`, string, required: Data to post in the body
- `token`, string, optional: Bearer token for authorization
- `headers`, object, optional: Additional headers to include in the request

## Argument template
```json
{
  "url": "https://example.com/resource",
  "value": "sample_value_1",
  "token": "sample_token_1",
  "headers": {}
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for playwright_post
```json
{
  "url": "https://example.com/resource",
  "value": "sample_value_1"
}
```
- Richer invocation that uses optional controls for playwright_post
```json
{
  "url": "https://example.com/resource",
  "value": "sample_value_2",
  "token": "sample_token_2",
  "headers": {}
}
```
