# trigger-long-running-operation

**Condition:** `multi_candidate_skill`

## Summary
Demonstrates a long running operation with progress updates. This tool has no required input fields.

## When to use
- Use `trigger-long-running-operation` when the user's request directly matches this tool's purpose.
- This tool has no required input fields.
- Optional controls include `duration`, `steps`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `duration`, string, optional: No description provided.
- `steps`, number, optional: No description provided.

## Argument template
```json
{
  "duration": "sample_duration_4",
  "steps": 4.0
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Richer invocation that uses optional controls for trigger-long-running-operation
```json
{
  "duration": "sample_duration_2",
  "steps": 2.0
}
```
- Optional, enum, nested, or array argument example.
```json
{
  "duration": "sample_duration_4",
  "steps": 4.0
}
```
