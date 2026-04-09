# search_docs

**Condition:** `autoskill_base`

## Summary
Search documents using a keyword query. Provide the required field `query`.

## When to use
- Use `search_docs` when the user's request directly matches this tool's purpose.
- Provide the required field `query`.
- Optional control is available through `top_k` when the request needs extra specificity.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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

## Semantic hints
No explicit semantic hints for this condition.

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
