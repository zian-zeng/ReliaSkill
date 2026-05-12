# puppeteer_screenshot

**Condition:** `multi_candidate_skill`

## Summary
Take a screenshot of the current page or a specific element. Provide the required field `name`.

## When to use
- Use `puppeteer_screenshot` when the user's request directly matches this tool's purpose.
- Provide the required field `name`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `name`, string, required: Name for the screenshot
- `selector`, string, optional: CSS selector for element to screenshot
- `width`, number, optional: Width in pixels (default: 800)
- `height`, number, optional: Height in pixels (default: 600)
- `encoded`, boolean, optional: If true, capture the screenshot as a base64-encoded data URI (as text) instead of binary image content. Default false.

## Argument template
```json
{
  "name": "sample-name",
  "selector": "sample_selector_1",
  "width": 1.0,
  "height": 1.0,
  "encoded": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for puppeteer_screenshot
```json
{
  "name": "sample-name"
}
```
- Richer invocation that uses optional controls for puppeteer_screenshot
```json
{
  "name": "sample-name",
  "selector": "sample_selector_2",
  "width": 2.0,
  "height": 2.0,
  "encoded": true
}
```
