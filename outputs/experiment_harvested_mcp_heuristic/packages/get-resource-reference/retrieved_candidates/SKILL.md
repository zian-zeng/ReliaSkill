# get-resource-reference

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `get-resource-reference` over nearby tools using cues like get-resource-reference, clients, resourcetype, resourceid.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `get-resource-reference` when the request matches its role.
- Shortlist: get-resource-reference, get-resource-links, get-annotated-message.
- Returns a resource reference that can be used by MCP clients
- Returns a resource reference that can be used by MCP clients

## When not to use
- Do not confuse `get-resource-reference` with `get-resource-links`: Returns up to ten resource links that reference different types of resources
- Do not confuse `get-resource-reference` with `get-annotated-message`: Demonstrates how annotations can be used to provide metadata about content.

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
- Minimal routed call for get-resource-reference
```json
{
  "resourceType": "sample_resourceType_1",
  "resourceId": "sample_resourceId_1"
}
```
- Full routed call for get-resource-reference
```json
{
  "resourceType": "sample_resourceType_2",
  "resourceId": "sample_resourceId_2"
}
```
