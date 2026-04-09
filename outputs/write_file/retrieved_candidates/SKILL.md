# write_file

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `write_file` over nearby tools using cues like write_file, completely, overwrite, existing.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `write_file` when the request matches its role.
- Shortlist: write_file, read_text_file, create_directory.
- Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories.
- Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories.

## When not to use
- Do not confuse `write_file` with `read_text_file`: Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the head parameter to read only the first N lines of a file, or the tail parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.
- Do not confuse `write_file` with `create_directory`: Create a new directory or ensure a directory exists. Can create multiple nested directories in one operation. If the directory already exists, this operation will succeed silently. Perfect for setting up directory structures for projects or ensuring required paths exist. Only works within allowed directories.

## Arguments
- `path`, string, required: Destination file path within an allowed directory.
- `content`, string, required: Full file contents to write.

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
