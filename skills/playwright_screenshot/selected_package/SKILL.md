# playwright_screenshot

**Condition:** `multi_candidate_skill`

## Summary
Take a screenshot of the current page or a specific element. Provide the required field `name`.

## When to use
- Use `playwright_screenshot` when the user's request directly matches this tool's purpose.
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
- `storeBase64`, boolean, optional: Store screenshot in base64 format (default: true)
- `fullPage`, boolean, optional: Store screenshot of the entire page (default: false)
- `savePng`, boolean, optional: Save screenshot as PNG file (default: false)
- `downloadsDir`, string, optional: Custom downloads directory path (default: user's Downloads folder)

## Argument template
```json
{
  "name": "sample-name",
  "selector": "sample_selector_1",
  "width": 1.0,
  "height": 1.0,
  "storeBase64": false,
  "fullPage": false,
  "savePng": false,
  "downloadsDir": "sample_downloadsDir_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for playwright_screenshot
```json
{
  "name": "sample-name"
}
```
- Richer invocation that uses optional controls for playwright_screenshot
```json
{
  "name": "sample-name",
  "selector": "sample_selector_2",
  "width": 2.0,
  "height": 2.0,
  "storeBase64": true,
  "fullPage": true,
  "savePng": true,
  "downloadsDir": "sample_downloadsDir_2"
}
```
