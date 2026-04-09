# echo

**Condition:** `schema_only`

## Summary
Echoes back the input string

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

## Arguments
- `message`, string, required: No description provided.

## Argument template
```json
{
  "message": "sample_message_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid call for echo
```json
{
  "message": "sample_message_1"
}
```
- Schema-aligned full call for echo
```json
{
  "message": "sample_message_2"
}
```
