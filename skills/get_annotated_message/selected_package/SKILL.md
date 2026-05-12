# get-annotated-message

**Condition:** `multi_candidate_skill`

## Summary
Demonstrates how annotations can be used to provide metadata about content. Provide the required field `messageType`.

## When to use
- Use `get-annotated-message` when the user's request directly matches this tool's purpose.
- Provide the required field `messageType`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `messageType`, string, required: No description provided.
- `includeImage`, string, optional: No description provided.

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
  "messageType": "sample_messageType_1"
}
```
- Richer invocation that uses optional controls for get-annotated-message
```json
{
  "messageType": "sample_messageType_2",
  "includeImage": "sample_includeImage_2"
}
```
