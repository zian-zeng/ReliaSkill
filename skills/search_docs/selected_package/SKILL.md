# search_docs

**Condition:** `multi_candidate_skill`

## Summary
Search documents using a keyword query. Provide the required field `query`.

## When to use
- Use `search_docs` when the user's request directly matches this tool's purpose.
- Provide the required field `query`.
- Optional control is available through `top_k` when the request needs extra specificity.
- Use examples to map paraphrases into schema-faithful arguments.

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
- Required-argument dev behavior example.
```json
{
  "query": "sample query"
}
```
- Optional, enum, nested, or array argument example.
```json
{
  "query": "sample query",
  "top_k": 5
}
```
