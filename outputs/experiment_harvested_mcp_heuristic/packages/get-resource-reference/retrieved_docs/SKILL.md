# get-resource-reference

**Condition:** `retrieved_docs`

## Summary
Returns a resource reference that can be used by MCP clients Get Resource Reference Tool

## When to use
- Returns a resource reference that can be used by MCP clients
- Get Resource Reference Tool
- resourceType required
- resourceId required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for get-resource-reference
```json
{
  "resourceType": "sample_resourceType_1",
  "resourceId": "sample_resourceId_1"
}
```
- Retrieved-docs fuller call for get-resource-reference
```json
{
  "resourceType": "sample_resourceType_2",
  "resourceId": "sample_resourceId_2"
}
```
