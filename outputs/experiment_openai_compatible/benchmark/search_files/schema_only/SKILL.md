# search_files

**Condition:** `schema_only`

## Summary
Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you do not know their exact location. Only searches within allowed directories.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

## Arguments
- `path`, string, required: Base directory to search within an allowed directory.
- `pattern`, string, required: Glob-style pattern to match.
- `excludePatterns`, array, optional, default=[]: Optional glob patterns to exclude.

## Argument template
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_1",
  "excludePatterns": []
}
```

## Examples
- Minimal valid call for search_files
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_1"
}
```
- Schema-aligned full call for search_files
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_2",
  "excludePatterns": []
}
```
