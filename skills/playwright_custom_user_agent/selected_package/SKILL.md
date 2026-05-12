# playwright_custom_user_agent

**Condition:** `multi_candidate_skill`

## Summary
Set a custom User Agent for the browser. Provide the required field `userAgent`.

## When to use
- Use `playwright_custom_user_agent` when the user's request directly matches this tool's purpose.
- Provide the required field `userAgent`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `userAgent`, string, required: Custom User Agent for the Playwright browser instance

## Argument template
```json
{
  "userAgent": "sample_userAgent_4"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for playwright_custom_user_agent
```json
{
  "userAgent": "sample_userAgent_1"
}
```
- Richer invocation that uses optional controls for playwright_custom_user_agent
```json
{
  "userAgent": "sample_userAgent_2"
}
```
- Required-argument dev behavior example.
```json
{
  "userAgent": "sample_userAgent_3"
}
```
- Optional, enum, nested, or array argument example.
```json
{
  "userAgent": "sample_userAgent_4"
}
```
