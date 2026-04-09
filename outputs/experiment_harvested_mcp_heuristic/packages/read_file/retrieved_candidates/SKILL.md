# read_file

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `read_file` over nearby tools using cues like read_file, deprecated, instead..

## When to use
- Retrieve a shortlist of nearby tools first, then choose `read_file` when the request matches its role.
- Shortlist: read_file, read_text_file, read_multiple_files.
- Read the complete contents of a file as text. DEPRECATED: Use read_text_file instead.
- Read the complete contents of a file as text. DEPRECATED: Use read_text_file instead.

## When not to use
- Do not confuse `read_file` with `read_text_file`: Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the 'head' parameter to read only the first N lines of a file, or the 'tail' parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.
- Do not confuse `read_file` with `read_multiple_files`: Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories.

## Arguments
- `path`, string, required: No description provided.
- `tail`, number, optional: No description provided.
- `head`, number, optional: No description provided.

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
- Minimal routed call for read_file
```json
{
  "path": "data/sample.txt"
}
```
- Full routed call for read_file
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
