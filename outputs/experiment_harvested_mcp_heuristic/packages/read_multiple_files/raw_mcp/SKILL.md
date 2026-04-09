# read_multiple_files

**Condition:** `raw_mcp`

## Summary
Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories.

## When to use
- Use the original MCP description and schema directly without added guidance.
- Consult schema.normalized.json for the exact argument contract.

## When not to use
- Do not assume example calls or usage heuristics beyond the original schema.

## Arguments
- `paths`, array, required: No description provided.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Semantic hints
No explicit semantic hints for this condition.

## Examples
No synthesized examples for this condition.
