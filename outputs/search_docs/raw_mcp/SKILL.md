# search_docs

**Condition:** `raw_mcp`

## Summary
Search documents using a keyword query.

## When to use
- Use the original MCP description and schema directly without added guidance.
- Consult schema.normalized.json for the exact argument contract.

## When not to use
- Do not assume example calls or usage heuristics beyond the original schema.

## Arguments
- `query`, string, required: Search query.
- `top_k`, integer, optional, default=5: Maximum number of results.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Examples
No synthesized examples for this condition.
