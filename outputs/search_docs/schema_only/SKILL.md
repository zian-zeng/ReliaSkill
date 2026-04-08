# search_docs

**Condition:** `schema_only`

## Summary
Search documents using a keyword query.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

## Arguments
- `query`, string, required: Search query.
- `top_k`, integer, optional, default=5: Maximum number of results.

## Argument template
```json
{
  "query": "sample query",
  "top_k": 5
}
```

## Examples
- Minimal valid call for search_docs
```json
{
  "query": "sample query"
}
```
- Schema-aligned full call for search_docs
```json
{
  "query": "sample query",
  "top_k": 5
}
```
