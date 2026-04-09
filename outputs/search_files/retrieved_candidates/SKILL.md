# search_files

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `search_files` over nearby tools using cues like search_files, recursively, search, matching.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `search_files` when the request matches its role.
- Shortlist: search_files, list_directory, read_text_file.
- Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you do not know their exact location. Only searches within allowed directories.
- Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you do not know their exact location. Only searches within allowed directories.

## When not to use
- Do not confuse `search_files` with `list_directory`: Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory. Only works within allowed directories.
- Do not confuse `search_files` with `read_text_file`: Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the head parameter to read only the first N lines of a file, or the tail parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.

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
- Minimal routed call for search_files
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_1"
}
```
- Full routed call for search_files
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_2",
  "excludePatterns": []
}
```
- Route file discovery requests with recursive glob patterns to this tool.
```json
{
  "path": "docs",
  "pattern": "**/*.md",
  "excludePatterns": []
}
```
