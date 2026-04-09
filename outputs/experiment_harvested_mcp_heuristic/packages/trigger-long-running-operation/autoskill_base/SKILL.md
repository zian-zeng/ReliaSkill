# trigger-long-running-operation

**Condition:** `autoskill_base`

## Summary
Demonstrates a long running operation with progress updates. Provide all required fields: `duration`, and `steps`.

## When to use
- Use `trigger-long-running-operation` when the user's request directly matches this tool's purpose.
- Provide all required fields: `duration`, and `steps`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

## Arguments
- `duration`, string, required: No description provided.
- `steps`, number, required: No description provided.

## Argument template
```json
{
  "duration": "sample_duration_1",
  "steps": 1.0
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for trigger-long-running-operation
```json
{
  "duration": "sample_duration_1",
  "steps": 1.0
}
```
- Richer invocation that uses optional controls for trigger-long-running-operation
```json
{
  "duration": "sample_duration_2",
  "steps": 2.0
}
```
