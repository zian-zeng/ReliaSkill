# get-annotated-message

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `get-annotated-message` over nearby tools using cues like get-annotated-message, demonstrates, annotations, provide.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `get-annotated-message` when the request matches its role.
- Shortlist: get-annotated-message, get-resource-reference, get_file_info.
- Demonstrates how annotations can be used to provide metadata about content.
- Demonstrates how annotations can be used to provide metadata about content.

## When not to use
- Do not confuse `get-annotated-message` with `get-resource-reference`: Returns a resource reference that can be used by MCP clients
- Do not confuse `get-annotated-message` with `get_file_info`: Retrieve detailed metadata about a file or directory. Returns comprehensive information including size, creation time, last modified time, permissions, and type. This tool is perfect for understanding file characteristics without reading the actual content. Only works within allowed directories.

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
- Minimal routed call for get-annotated-message
```json
{
  "messageType": "sample_messageType_1",
  "includeImage": "sample_includeImage_1"
}
```
- Full routed call for get-annotated-message
```json
{
  "messageType": "sample_messageType_2",
  "includeImage": "sample_includeImage_2"
}
```
