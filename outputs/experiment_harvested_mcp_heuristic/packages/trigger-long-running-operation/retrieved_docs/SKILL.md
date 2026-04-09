# trigger-long-running-operation

**Condition:** `retrieved_docs`

## Summary
Demonstrates a long running operation with progress updates. Trigger Long Running Operation Tool

## When to use
- Demonstrates a long running operation with progress updates.
- Trigger Long Running Operation Tool
- duration required
- steps required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for trigger-long-running-operation
```json
{
  "duration": "sample_duration_1",
  "steps": 1.0
}
```
- Retrieved-docs fuller call for trigger-long-running-operation
```json
{
  "duration": "sample_duration_2",
  "steps": 2.0
}
```
