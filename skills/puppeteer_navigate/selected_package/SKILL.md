# puppeteer_navigate

**Condition:** `multi_candidate_skill`

## Summary
Navigate to a URL. Provide the required field `url`.

## When to use
- Use `puppeteer_navigate` when the user's request directly matches this tool's purpose.
- Provide the required field `url`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `url`, string, required: URL to navigate to
- `launchOptions`, object, optional: PuppeteerJS LaunchOptions. Default null. If changed and not null, browser restarts. Example: { headless: true, args: ['--no-sandbox'] }
- `allowDangerous`, boolean, optional: Allow dangerous LaunchOptions that reduce security. When false, dangerous args like --no-sandbox will throw errors. Default false.

## Argument template
```json
{
  "url": "https://example.com/resource",
  "launchOptions": {},
  "allowDangerous": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for puppeteer_navigate
```json
{
  "url": "https://example.com/resource"
}
```
- Richer invocation that uses optional controls for puppeteer_navigate
```json
{
  "url": "https://example.com/resource",
  "launchOptions": {},
  "allowDangerous": true
}
```
