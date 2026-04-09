# get-resource-reference

**Condition:** `schema_only`

## Summary
Returns a resource reference that can be used by MCP clients

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for get-resource-reference
```json
{
  "resourceType": "sample_resourceType_1",
  "resourceId": "sample_resourceId_1"
}
```
- Schema-aligned full call for get-resource-reference
```json
{
  "resourceType": "sample_resourceType_2",
  "resourceId": "sample_resourceId_2"
}
```
