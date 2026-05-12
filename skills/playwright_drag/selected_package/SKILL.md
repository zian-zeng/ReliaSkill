# playwright_drag

**Condition:** `multi_candidate_skill`

## Summary
Drag an element to a target location. Provide all required fields: `sourceSelector`, and `targetSelector`.

## When to use
- Use `playwright_drag` when the user's request directly matches this tool's purpose.
- Provide all required fields: `sourceSelector`, and `targetSelector`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `sourceSelector`, string, required: CSS selector for the element to drag
- `targetSelector`, string, required: CSS selector for the target location

## Argument template
```json
{
  "sourceSelector": "sample_sourceSelector_1",
  "targetSelector": "sample_targetSelector_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for playwright_drag
```json
{
  "sourceSelector": "sample_sourceSelector_1",
  "targetSelector": "sample_targetSelector_1"
}
```
- Richer invocation that uses optional controls for playwright_drag
```json
{
  "sourceSelector": "sample_sourceSelector_2",
  "targetSelector": "sample_targetSelector_2"
}
```
