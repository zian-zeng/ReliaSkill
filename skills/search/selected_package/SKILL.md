# search

**Condition:** `multi_candidate_skill`

## Summary
Perform a web search query. Provide all required fields: `query`, and `num`.

## When to use
- Use `search` when the user's request directly matches this tool's purpose.
- Provide all required fields: `query`, and `num`.
- Use only when the request clearly needs `search`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use for adjacent tools with similar names, descriptions, or arguments.
- Do not use for read/write, search/fetch, create/update, delete/preview, or execute/explain mismatches.
- If the request lacks required fields, abstain or ask for clarification.

## Arguments
- `query`, string, required: Search query
- `num`, number, required: Number of results (1-10)

## Argument template
```json
{
  "query": "sample query",
  "num": 1.0
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for search
```json
{
  "query": "sample query",
  "num": 1.0
}
```
- Richer invocation that uses optional controls for search
```json
{
  "query": "sample query",
  "num": 2.0
}
```
