# playwright_navigate

**Condition:** `multi_candidate_skill`

## Summary
Navigate to a URL. Provide the required field `url`.

## When to use
- Use `playwright_navigate` when the user's request directly matches this tool's purpose.
- Provide the required field `url`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `browserType`: 'chromium', 'firefox', 'webkit'.
- Do not use when required inputs are missing.

## Arguments
- `url`, string, required: URL to navigate to the website specified
- `browserType`, string, optional, enum=['chromium', 'firefox', 'webkit']: Browser type to use (chromium, firefox, webkit). Defaults to chromium
- `width`, number, optional: Viewport width in pixels (default: 1280)
- `height`, number, optional: Viewport height in pixels (default: 720)
- `timeout`, number, optional: Navigation timeout in milliseconds
- `waitUntil`, string, optional: Navigation wait condition
- `headless`, boolean, optional: Run browser in headless mode (default: false)

## Argument template
```json
{
  "url": "https://example.com/resource",
  "browserType": "chromium",
  "width": 1.0,
  "height": 1.0,
  "timeout": 1.0,
  "waitUntil": "sample_waitUntil_1",
  "headless": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for playwright_navigate
```json
{
  "url": "https://example.com/resource"
}
```
- Richer invocation that uses optional controls for playwright_navigate
```json
{
  "url": "https://example.com/resource",
  "browserType": "firefox",
  "width": 2.0,
  "height": 2.0,
  "timeout": 2.0,
  "waitUntil": "sample_waitUntil_2",
  "headless": true
}
```
