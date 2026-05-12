# playwright_press_key

**Condition:** `multi_candidate_skill`

## Summary
Press a keyboard key. Provide the required field `key`.

## When to use
- Use `playwright_press_key` when the user's request directly matches this tool's purpose.
- Provide the required field `key`.
- Optional control is available through `selector` when the request needs extra specificity.
- Use only when the request clearly needs `playwright_press_key`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use for adjacent tools with similar names, descriptions, or arguments.
- Do not use for read/write, search/fetch, create/update, delete/preview, or execute/explain mismatches.
- If the request lacks required fields, abstain or ask for clarification.

## Arguments
- `key`, string, required: Key to press (e.g. 'Enter', 'ArrowDown', 'a')
- `selector`, string, optional: Optional CSS selector to focus before pressing key

## Argument template
```json
{
  "key": "sample_key_1",
  "selector": "sample_selector_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for playwright_press_key
```json
{
  "key": "sample_key_1"
}
```
- Richer invocation that uses optional controls for playwright_press_key
```json
{
  "key": "sample_key_2",
  "selector": "sample_selector_2"
}
```
