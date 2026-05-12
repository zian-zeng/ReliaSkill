# playwright_fill

**Condition:** `multi_candidate_skill`

## Summary
fill out an input field. Provide all required fields: `selector`, and `value`.

## When to use
- Use `playwright_fill` when the user's request directly matches this tool's purpose.
- Provide all required fields: `selector`, and `value`.
- Use only when the request clearly needs `playwright_fill`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use for adjacent tools with similar names, descriptions, or arguments.
- Do not use for read/write, search/fetch, create/update, delete/preview, or execute/explain mismatches.
- If the request lacks required fields, abstain or ask for clarification.

## Arguments
- `selector`, string, required: CSS selector for input field
- `value`, string, required: Value to fill

## Argument template
```json
{
  "selector": "sample_selector_1",
  "value": "sample_value_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for playwright_fill
```json
{
  "selector": "sample_selector_1",
  "value": "sample_value_1"
}
```
- Richer invocation that uses optional controls for playwright_fill
```json
{
  "selector": "sample_selector_2",
  "value": "sample_value_2"
}
```
