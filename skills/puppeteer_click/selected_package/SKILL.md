# puppeteer_click

**Condition:** `multi_candidate_skill`

## Summary
Click an element on the page. Provide the required field `selector`.

## When to use
- Use `puppeteer_click` when the user's request directly matches this tool's purpose.
- Provide the required field `selector`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `selector`, string, required: CSS selector for element to click

## Argument template
```json
{
  "selector": "sample_selector_4"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for puppeteer_click
```json
{
  "selector": "sample_selector_1"
}
```
- Richer invocation that uses optional controls for puppeteer_click
```json
{
  "selector": "sample_selector_2"
}
```
- Required-argument dev behavior example.
```json
{
  "selector": "sample_selector_3"
}
```
- Optional, enum, nested, or array argument example.
```json
{
  "selector": "sample_selector_4"
}
```
