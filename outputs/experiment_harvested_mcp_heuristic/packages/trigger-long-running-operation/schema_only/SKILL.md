# trigger-long-running-operation

**Condition:** `schema_only`

## Summary
Demonstrates a long running operation with progress updates.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for trigger-long-running-operation
```json
{
  "duration": "sample_duration_1",
  "steps": 1.0
}
```
- Schema-aligned full call for trigger-long-running-operation
```json
{
  "duration": "sample_duration_2",
  "steps": 2.0
}
```
