# edit_file

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `edit_file` over nearby tools using cues like edit_file, make, line-based, edits.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `edit_file` when the request matches its role.
- Shortlist: edit_file, read_multiple_files, read_text_file.
- Make line-based edits to a text file. Each edit replaces exact line sequences with new content. Returns a git-style diff showing the changes made. Only works within allowed directories.
- Make line-based edits to a text file. Each edit replaces exact line sequences with new content. Returns a git-style diff showing the changes made. Only works within allowed directories.

## When not to use
- Do not confuse `edit_file` with `read_multiple_files`: Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories.
- Do not confuse `edit_file` with `read_text_file`: Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the 'head' parameter to read only the first N lines of a file, or the 'tail' parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.

## Arguments
- `path`, string, required: No description provided.
- `edits`, array, required: No description provided.
- `dryRun`, boolean, required: No description provided.

## Argument template
```json
{
  "path": "data/sample.txt",
  "edits": [
    {}
  ],
  "dryRun": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for edit_file
```json
{
  "path": "data/sample.txt",
  "edits": [
    {}
  ],
  "dryRun": false
}
```
- Full routed call for edit_file
```json
{
  "path": "data/sample.txt",
  "edits": [
    {}
  ],
  "dryRun": true
}
```
