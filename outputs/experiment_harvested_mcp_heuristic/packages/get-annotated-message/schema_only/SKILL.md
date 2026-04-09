# get-annotated-message

**Condition:** `schema_only`

## Summary
Demonstrates how annotations can be used to provide metadata about content.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

## Arguments
- `messageType`, string, required: No description provided.
- `includeImage`, string, required: No description provided.

## Argument template
```json
{
  "messageType": "sample_messageType_1",
  "includeImage": "sample_includeImage_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid call for get-annotated-message
```json
{
  "messageType": "sample_messageType_1",
  "includeImage": "sample_includeImage_1"
}
```
- Schema-aligned full call for get-annotated-message
```json
{
  "messageType": "sample_messageType_2",
  "includeImage": "sample_includeImage_2"
}
```
