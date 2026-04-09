# get-resource-links

**Condition:** `schema_only`

## Summary
Returns up to ten resource links that reference different types of resources

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for get-resource-links
```json
{
  "count": "sample_count_1"
}
```
- Schema-aligned full call for get-resource-links
```json
{
  "count": "sample_count_2"
}
```
