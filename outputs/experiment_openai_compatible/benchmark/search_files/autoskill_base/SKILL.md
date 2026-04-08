# search_files

**Condition:** `autoskill_base`

## Summary
Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you do not know their exact location. Only searches within allowed directories. Provide all required fields: `path`, and `pattern`.

## When to use
- Use `search_files` when the user's request directly matches this tool's purpose.
- Provide all required fields: `path`, and `pattern`.
- Optional control is available through `excludePatterns` when the request needs extra specificity.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

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
- Minimal valid request that satisfies the required fields for search_files
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_1"
}
```
- Richer invocation that uses optional controls for search_files
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_2",
  "excludePatterns": []
}
```
