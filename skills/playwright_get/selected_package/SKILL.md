# playwright_get

**Condition:** `multi_candidate_skill`

## Summary
Perform an HTTP GET request. Provide the required field `url`.

## When to use
- Use `playwright_get` when the user's request directly matches this tool's purpose.
- Provide the required field `url`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `url`, string, required: URL to perform GET operation

## Argument template
```json
{
  "url": "https://example.com/resource"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for playwright_get
```json
{
  "url": "https://example.com/resource"
}
```
- Richer invocation that uses optional controls for playwright_get
```json
{
  "url": "https://example.com/resource"
}
```
- Required-argument dev behavior example.
```json
{
  "url": "https://example.com/resource"
}
```
