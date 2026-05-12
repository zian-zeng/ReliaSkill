# playwright_iframe_fill

**Condition:** `multi_candidate_skill`

## Summary
Fill an element in an iframe on the page. Provide all required fields: `iframeSelector`, `selector`, and `value`.

## When to use
- Use `playwright_iframe_fill` when the user's request directly matches this tool's purpose.
- Provide all required fields: `iframeSelector`, `selector`, and `value`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `iframeSelector`, string, required: CSS selector for the iframe containing the element to fill
- `selector`, string, required: CSS selector for the element to fill
- `value`, string, required: Value to fill

## Argument template
```json
{
  "iframeSelector": "sample_iframeSelector_1",
  "selector": "sample_selector_1",
  "value": "sample_value_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for playwright_iframe_fill
```json
{
  "iframeSelector": "sample_iframeSelector_1",
  "selector": "sample_selector_1",
  "value": "sample_value_1"
}
```
- Richer invocation that uses optional controls for playwright_iframe_fill
```json
{
  "iframeSelector": "sample_iframeSelector_2",
  "selector": "sample_selector_2",
  "value": "sample_value_2"
}
```
