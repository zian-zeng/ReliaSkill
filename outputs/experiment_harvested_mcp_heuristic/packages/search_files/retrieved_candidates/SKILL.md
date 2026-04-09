# search_files

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `search_files` over nearby tools using cues like search_files, recursively, search, matching.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `search_files` when the request matches its role.
- Shortlist: search_files, list_directory, list_directory_with_sizes.
- Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you don't know their exact location. Only searches within allowed directories.
- Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you don't know their exact location. Only searches within allowed directories.

## When not to use
- Do not confuse `search_files` with `list_directory`: Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory. Only works within allowed directories.
- Do not confuse `search_files` with `list_directory_with_sizes`: Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within a directory. Only works within allowed directories.

## Arguments
- `path`, string, required: No description provided.
- `pattern`, string, required: No description provided.
- `excludePatterns`, array, required: No description provided.

## Argument template
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_1",
  "excludePatterns": [
    "sample_excludePatterns_item_1"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for search_files
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_1",
  "excludePatterns": [
    "sample_excludePatterns_item_1"
  ]
}
```
- Full routed call for search_files
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_2",
  "excludePatterns": [
    "sample_excludePatterns_item_2"
  ]
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
