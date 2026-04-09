# get-annotated-message

**Condition:** `retrieved_docs`

## Summary
Demonstrates how annotations can be used to provide metadata about content. Get Annotated Message Tool

## When to use
- Demonstrates how annotations can be used to provide metadata about content.
- Get Annotated Message Tool
- includeImage required
- messageType required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for get-annotated-message
```json
{
  "messageType": "sample_messageType_1",
  "includeImage": "sample_includeImage_1"
}
```
- Retrieved-docs fuller call for get-annotated-message
```json
{
  "messageType": "sample_messageType_2",
  "includeImage": "sample_includeImage_2"
}
```
