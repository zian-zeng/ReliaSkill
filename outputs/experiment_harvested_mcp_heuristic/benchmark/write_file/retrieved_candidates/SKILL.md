# write_file

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `write_file` over nearby tools using cues like write_file, create, completely, overwrite.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `write_file` when the request matches its role.
- Shortlist: write_file, read_multiple_files, read_text_file.
- Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories.
- Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories.

## When not to use
- Do not confuse `write_file` with `read_multiple_files`: Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories.
- Do not confuse `write_file` with `read_text_file`: Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the 'head' parameter to read only the first N lines of a file, or the 'tail' parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.

## Arguments
- `path`, string, required: No description provided.
- `content`, string, required: No description provided.

## Argument template
```json
{
  "path": "data/sample.txt",
  "content": "sample_content_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for write_file
```json
{
  "path": "data/sample.txt",
  "content": "sample_content_1"
}
```
- Full routed call for write_file
```json
{
  "path": "data/sample.txt",
  "content": "sample_content_2"
}
```
- Route write-content requests to this file writer.
```json
{
  "path": "docs/notes.txt",
  "content": "Release checklist"
}
```
