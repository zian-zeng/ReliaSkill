# search_docs

**Condition:** `autoskill_base`

## Summary
Search documents using a keyword query. Provide the required field `query`.

## When to use
- Use `search_docs` when the user's request directly matches this tool's purpose.
- Provide the required field `query`.
- Optional control is available through `top_k` when the request needs extra specificity.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

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
- Minimal valid request that satisfies the required fields for search_docs
```json
{
  "query": "sample query"
}
```
- Richer invocation that uses optional controls for search_docs
```json
{
  "query": "sample query",
  "top_k": 5
}
```
