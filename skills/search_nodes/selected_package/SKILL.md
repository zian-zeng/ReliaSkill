# search_nodes

**Condition:** `multi_candidate_skill`

## Summary
Search for nodes in the knowledge graph based on a query. Provide the required field `query`.

## When to use
- Use `search_nodes` when the user's request directly matches this tool's purpose.
- Provide the required field `query`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `query`, string, required: No description provided.

## Argument template
```json
{
  "query": "sample query"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for search_nodes
```json
{
  "query": "sample query"
}
```
- Richer invocation that uses optional controls for search_nodes
```json
{
  "query": "sample query"
}
```
- Required-argument dev behavior example.
```json
{
  "query": "sample query"
}
```
