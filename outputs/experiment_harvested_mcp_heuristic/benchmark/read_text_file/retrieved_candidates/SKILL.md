# read_text_file

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `read_text_file` over nearby tools using cues like read_text_file, complete, from, system.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `read_text_file` when the request matches its role.
- Shortlist: read_text_file, read_multiple_files, get_file_info.
- Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the 'head' parameter to read only the first N lines of a file, or the 'tail' parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.
- Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the 'head' parameter to read only the first N lines of a file, or the 'tail' parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.

## When not to use
- Do not confuse `read_text_file` with `read_multiple_files`: Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories.
- Do not confuse `read_text_file` with `get_file_info`: Retrieve detailed metadata about a file or directory. Returns comprehensive information including size, creation time, last modified time, permissions, and type. This tool is perfect for understanding file characteristics without reading the actual content. Only works within allowed directories.

## Arguments
- `path`, string, required: No description provided.
- `tail`, number, required: No description provided.
- `head`, number, required: No description provided.

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
  "path": "data/sample.txt",
  "tail": 1.0,
  "head": 1.0
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
