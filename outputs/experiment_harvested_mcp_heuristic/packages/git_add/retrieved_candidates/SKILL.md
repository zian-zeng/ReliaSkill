# git_add

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `git_add` over nearby tools using cues like git_add, adds, staging, area.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `git_add` when the request matches its role.
- Shortlist: git_add, read_multiple_files, read_text_file.
- Adds file contents to the staging area
- Adds file contents to the staging area

## When not to use
- Do not confuse `git_add` with `read_multiple_files`: Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories.
- Do not confuse `git_add` with `read_text_file`: Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the 'head' parameter to read only the first N lines of a file, or the 'tail' parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.

## Arguments
- `repo_path`, string, required: No description provided.
- `files`, array, required: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "files": [
    "data/sample.txt"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for git_add
```json
{
  "repo_path": "data/sample.txt",
  "files": [
    "data/sample.txt"
  ]
}
```
