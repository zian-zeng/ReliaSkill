# playwright_assert_response

**Condition:** `multi_candidate_skill`

## Summary
Wait for and validate a previously initiated HTTP response wait operation. Provide the required field `id`.

## When to use
- Use `playwright_assert_response` when the user's request directly matches this tool's purpose.
- Provide the required field `id`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `id`, string, required: Identifier of the HTTP response initially expected using `Playwright_expect_response`.
- `value`, string, optional: Data to expect in the body of the HTTP response. If provided, the assertion will fail if this value is not found in the response body.

## Argument template
```json
{
  "id": "sample-id-001",
  "value": "sample_value_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for playwright_assert_response
```json
{
  "id": "sample-id-001"
}
```
- Richer invocation that uses optional controls for playwright_assert_response
```json
{
  "id": "sample-id-001",
  "value": "sample_value_2"
}
```
