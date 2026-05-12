# playwright_expect_response

**Condition:** `multi_candidate_skill`

## Summary
Ask Playwright to start waiting for a HTTP response. This tool initiates the wait operation but does not wait for its completion. Provide all required fields: `id`, and `url`.

## When to use
- Use `playwright_expect_response` when the user's request directly matches this tool's purpose.
- Provide all required fields: `id`, and `url`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `id`, string, required: Unique & arbitrary identifier to be used for retrieving this response later with `Playwright_assert_response`.
- `url`, string, required: URL pattern to match in the response.

## Argument template
```json
{
  "id": "sample-id-001",
  "url": "https://example.com/resource"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for playwright_expect_response
```json
{
  "id": "sample-id-001",
  "url": "https://example.com/resource"
}
```
- Richer invocation that uses optional controls for playwright_expect_response
```json
{
  "id": "sample-id-001",
  "url": "https://example.com/resource"
}
```
