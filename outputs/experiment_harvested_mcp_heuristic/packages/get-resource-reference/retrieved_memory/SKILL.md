# get-resource-reference

**Condition:** `retrieved_memory`

## Summary
Returns a resource reference that can be used by MCP clients

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

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
- Minimal valid memory-backed call for get-resource-reference
```json
{
  "resourceType": "sample_resourceType_1",
  "resourceId": "sample_resourceId_1"
}
```
