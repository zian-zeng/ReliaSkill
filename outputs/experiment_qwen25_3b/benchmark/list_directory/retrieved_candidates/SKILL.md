# list_directory

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `list_directory` over nearby tools using cues like list_directory, listing, specified, path..

## When to use
- Retrieve a shortlist of nearby tools first, then choose `list_directory` when the request matches its role.
- Shortlist: list_directory, search_files, read_text_file.
- Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory. Only works within allowed directories.
- Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory. Only works within allowed directories.

## When not to use
- Do not confuse `list_directory` with `search_files`: Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you do not know their exact location. Only searches within allowed directories.
- Do not confuse `list_directory` with `read_text_file`: Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the head parameter to read only the first N lines of a file, or the tail parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.

## Arguments
- `path`, string, required: Directory path to inspect within an allowed directory.

## Argument template
```json
{
  "path": "data/sample.txt"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for list_directory
```json
{
  "path": "data/sample.txt"
}
```
- Route inspect-directory requests here.
```json
{
  "path": "docs"
}
```
