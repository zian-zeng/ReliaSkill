# notes_semantic_search

**Condition:** `multi_candidate_skill`

## Summary
API-Bank-style local fixture retrieval tool for searching notes by query and tag filters. Provide the required field `query`.

## When to use
- Use `notes_semantic_search` when the user's request directly matches this tool's purpose.
- Provide the required field `query`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `query`, string, required: Search query.
- `tags`, array, optional: Tags to require.
- `limit`, integer, optional: Maximum notes to return.

## Argument template
```json
{
  "query": "sample query",
  "tags": [
    "sample_tags_item_1"
  ],
  "limit": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for notes_semantic_search
```json
{
  "query": "sample query"
}
```
- Richer invocation that uses optional controls for notes_semantic_search
```json
{
  "query": "sample query",
  "tags": [
    "sample_tags_item_2"
  ],
  "limit": 2
}
```
