# get-resource-links

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `get-resource-links` over nearby tools using cues like get-resource-links, links, different, types.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `get-resource-links` when the request matches its role.
- Shortlist: get-resource-links, get-resource-reference, list_allowed_directories.
- Returns up to ten resource links that reference different types of resources
- Returns up to ten resource links that reference different types of resources

## When not to use
- Do not confuse `get-resource-links` with `get-resource-reference`: Returns a resource reference that can be used by MCP clients
- Do not confuse `get-resource-links` with `list_allowed_directories`: Returns the list of directories that this server is allowed to access. Subdirectories within these allowed directories are also accessible. Use this to understand which directories and their nested paths are available before trying to access files.

## Arguments
- `count`, string, required: No description provided.

## Argument template
```json
{
  "count": "sample_count_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for get-resource-links
```json
{
  "count": "sample_count_1"
}
```
- Full routed call for get-resource-links
```json
{
  "count": "sample_count_2"
}
```
