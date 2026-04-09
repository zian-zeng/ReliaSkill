# search_files

**Condition:** `retrieved_docs`

## Summary
Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you do not know their exact location. Only searches within allowed directories. path required Base directory to search within an allowed directory.

## When to use
- Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you do not know their exact location. Only searches within allowed directories.
- path required Base directory to search within an allowed directory.
- excludePatterns optional Optional glob patterns to exclude. Default: [].
- pattern required Glob-style pattern to match.

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Retrieved-docs minimal call for search_files
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_1"
}
```
- Retrieved-docs fuller call for search_files
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_2",
  "excludePatterns": []
}
```
