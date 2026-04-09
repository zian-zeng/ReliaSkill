# gzip-file-as-resource

**Condition:** `raw_mcp`

## Summary
Compresses a single file using gzip compression. Depending upon the selected output type, returns either the compressed data as a gzipped resource or a resource link, allowing it to be downloaded in a subsequent request during the current session.

## When to use
- Use the original MCP description and schema directly without added guidance.
- Consult schema.normalized.json for the exact argument contract.

## When not to use
- Do not assume example calls or usage heuristics beyond the original schema.

## Arguments
- `name`, string, required: No description provided.
- `data`, string, required: No description provided.
- `outputType`, string, required: No description provided.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Semantic hints
No explicit semantic hints for this condition.

## Examples
No synthesized examples for this condition.
