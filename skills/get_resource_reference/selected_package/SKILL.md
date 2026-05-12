# get-resource-reference

**Condition:** `multi_candidate_skill`

## Summary
Returns a resource reference that can be used by MCP clients. This tool has no required input fields.

## When to use
- Use `get-resource-reference` when the user's request directly matches this tool's purpose.
- This tool has no required input fields.
- Optional controls include `resourceType`, `resourceId`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `resourceType`, string, optional: No description provided.
- `resourceId`, string, optional: No description provided.

## Argument template
```json
{
  "resourceType": "sample_resourceType_4",
  "resourceId": "sample_resourceId_4"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Richer invocation that uses optional controls for get-resource-reference
```json
{
  "resourceType": "sample_resourceType_2",
  "resourceId": "sample_resourceId_2"
}
```
- Optional, enum, nested, or array argument example.
```json
{
  "resourceType": "sample_resourceType_4",
  "resourceId": "sample_resourceId_4"
}
```
