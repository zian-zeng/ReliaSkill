# get-annotated-message

**Condition:** `retrieved_memory`

## Summary
Demonstrates how annotations can be used to provide metadata about content.

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

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
- Minimal valid memory-backed call for get-annotated-message
```json
{
  "messageType": "sample_messageType_1",
  "includeImage": "sample_includeImage_1"
}
```
