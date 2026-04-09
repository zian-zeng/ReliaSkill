# get-annotated-message

**Condition:** `autoskill_base`

## Summary
Demonstrates how annotations can be used to provide metadata about content. Provide all required fields: `messageType`, and `includeImage`.

## When to use
- Use `get-annotated-message` when the user's request directly matches this tool's purpose.
- Provide all required fields: `messageType`, and `includeImage`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
- Minimal valid request that satisfies the required fields for get-annotated-message
```json
{
  "messageType": "sample_messageType_1",
  "includeImage": "sample_includeImage_1"
}
```
- Richer invocation that uses optional controls for get-annotated-message
```json
{
  "messageType": "sample_messageType_2",
  "includeImage": "sample_includeImage_2"
}
```
