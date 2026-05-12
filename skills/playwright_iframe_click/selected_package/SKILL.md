# playwright_iframe_click

**Condition:** `multi_candidate_skill`

## Summary
Click an element in an iframe on the page. Provide all required fields: `iframeSelector`, and `selector`.

## When to use
- Use `playwright_iframe_click` when the user's request directly matches this tool's purpose.
- Provide all required fields: `iframeSelector`, and `selector`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `iframeSelector`, string, required: CSS selector for the iframe containing the element to click
- `selector`, string, required: CSS selector for the element to click

## Argument template
```json
{
  "iframeSelector": "sample_iframeSelector_1",
  "selector": "sample_selector_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for playwright_iframe_click
```json
{
  "iframeSelector": "sample_iframeSelector_1",
  "selector": "sample_selector_1"
}
```
- Richer invocation that uses optional controls for playwright_iframe_click
```json
{
  "iframeSelector": "sample_iframeSelector_2",
  "selector": "sample_selector_2"
}
```
