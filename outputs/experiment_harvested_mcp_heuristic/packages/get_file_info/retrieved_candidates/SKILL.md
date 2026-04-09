# get_file_info

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `get_file_info` over nearby tools using cues like get_file_info, retrieve, metadata, about.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `get_file_info` when the request matches its role.
- Shortlist: get_file_info, list_directory_with_sizes, list_directory.
- Retrieve detailed metadata about a file or directory. Returns comprehensive information including size, creation time, last modified time, permissions, and type. This tool is perfect for understanding file characteristics without reading the actual content. Only works within allowed directories.
- Retrieve detailed metadata about a file or directory. Returns comprehensive information including size, creation time, last modified time, permissions, and type. This tool is perfect for understanding file characteristics without reading the actual content. Only works within allowed directories.

## When not to use
- Do not confuse `get_file_info` with `list_directory_with_sizes`: Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within a directory. Only works within allowed directories.
- Do not confuse `get_file_info` with `list_directory`: Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory. Only works within allowed directories.

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
- Minimal routed call for get_file_info
```json
{
  "path": "data/sample.txt"
}
```
