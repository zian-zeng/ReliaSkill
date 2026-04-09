# read_text_file

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `read_text_file` over nearby tools using cues like read_text_file, read, complete, from.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `read_text_file` when the request matches its role.
- Shortlist: read_text_file, write_file, list_directory.
- Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the head parameter to read only the first N lines of a file, or the tail parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.
- Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the head parameter to read only the first N lines of a file, or the tail parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.

## When not to use
- Do not confuse `read_text_file` with `write_file`: Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories.
- Do not confuse `read_text_file` with `list_directory`: Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory. Only works within allowed directories.

## Arguments
- `path`, string, required: Path to the file within an allowed directory.
- `tail`, number, optional: If provided, returns only the last N lines of the file.
- `head`, number, optional: If provided, returns only the first N lines of the file.

## Argument template
```json
{
  "path": "data/sample.txt",
  "tail": 1.0,
  "head": 1.0
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for read_text_file
```json
{
  "path": "data/sample.txt"
}
```
- Full routed call for read_text_file
```json
{
  "path": "data/sample.txt",
  "tail": 2.0,
  "head": 2.0
}
```
- Read the first lines of a file after routing to the file reader.
```json
{
  "path": "src/app.py",
  "head": 8
}
```
- Read the last lines of a file after routing to the file reader.
```json
{
  "path": "logs/output.txt",
  "tail": 12
}
```
