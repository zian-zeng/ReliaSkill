# list_directory_with_sizes

**Condition:** `raw_mcp`

## Summary
Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within a directory. Only works within allowed directories.

## When to use
- Use the original MCP description and schema directly without added guidance.
- Consult schema.normalized.json for the exact argument contract.

## When not to use
- Do not assume example calls or usage heuristics beyond the original schema.

## Arguments
- `path`, string, required: No description provided.
- `sortBy`, string, required, enum=['name', 'size']: No description provided.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Semantic hints
No explicit semantic hints for this condition.

## Examples
No synthesized examples for this condition.
