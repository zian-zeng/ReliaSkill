# get-resource-reference

**Condition:** `autoskill_base`

## Summary
Returns a resource reference that can be used by MCP clients. Provide all required fields: `resourceType`, and `resourceId`.

## When to use
- Use `get-resource-reference` when the user's request directly matches this tool's purpose.
- Provide all required fields: `resourceType`, and `resourceId`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

## Arguments
- `resourceType`, string, required: No description provided.
- `resourceId`, string, required: No description provided.

## Argument template
```json
{
  "resourceType": "sample_resourceType_1",
  "resourceId": "sample_resourceId_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for get-resource-reference
```json
{
  "resourceType": "sample_resourceType_1",
  "resourceId": "sample_resourceId_1"
}
```
- Richer invocation that uses optional controls for get-resource-reference
```json
{
  "resourceType": "sample_resourceType_2",
  "resourceId": "sample_resourceId_2"
}
```
