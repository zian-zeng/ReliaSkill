# search_files

**Condition:** `raw_mcp`

## Summary
Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you do not know their exact location. Only searches within allowed directories.

## When to use
- Use the original MCP description and schema directly without added guidance.
- Consult schema.normalized.json for the exact argument contract.

## When not to use
- Do not assume example calls or usage heuristics beyond the original schema.

## Arguments
- `path`, string, required: Base directory to search within an allowed directory.
- `pattern`, string, required: Glob-style pattern to match.
- `excludePatterns`, array, optional, default=[]: Optional glob patterns to exclude.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Examples
No synthesized examples for this condition.
