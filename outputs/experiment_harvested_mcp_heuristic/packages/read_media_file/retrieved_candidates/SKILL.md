# read_media_file

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `read_media_file` over nearby tools using cues like read_media_file, image, audio, base64.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `read_media_file` when the request matches its role.
- Shortlist: read_media_file, get_file_info, read_text_file.
- Read an image or audio file. Returns the base64 encoded data and MIME type. Only works within allowed directories.
- Read an image or audio file. Returns the base64 encoded data and MIME type. Only works within allowed directories.

## When not to use
- Do not confuse `read_media_file` with `get_file_info`: Retrieve detailed metadata about a file or directory. Returns comprehensive information including size, creation time, last modified time, permissions, and type. This tool is perfect for understanding file characteristics without reading the actual content. Only works within allowed directories.
- Do not confuse `read_media_file` with `read_text_file`: Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the 'head' parameter to read only the first N lines of a file, or the 'tail' parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.

## Arguments
- `path`, string, required: No description provided.

## Argument template
```json
{
  "path": "data/sample.txt"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for read_media_file
```json
{
  "path": "data/sample.txt"
}
```
