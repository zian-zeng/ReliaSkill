# list_directory_with_sizes

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `list_directory_with_sizes` over nearby tools using cues like list_directory_with_sizes, sizes., useful, sizes.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `list_directory_with_sizes` when the request matches its role.
- Shortlist: list_directory_with_sizes, list_directory, get_file_info.
- Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within a directory. Only works within allowed directories.
- Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within a directory. Only works within allowed directories.

## When not to use
- Do not confuse `list_directory_with_sizes` with `list_directory`: Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory. Only works within allowed directories.
- Do not confuse `list_directory_with_sizes` with `get_file_info`: Retrieve detailed metadata about a file or directory. Returns comprehensive information including size, creation time, last modified time, permissions, and type. This tool is perfect for understanding file characteristics without reading the actual content. Only works within allowed directories.

## Arguments
- `path`, string, required: No description provided.
- `sortBy`, string, required, enum=['name', 'size']: No description provided.

## Argument template
```json
{
  "path": "data/sample.txt",
  "sortBy": "name"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for list_directory_with_sizes
```json
{
  "path": "data/sample.txt",
  "sortBy": "name"
}
```
- Full routed call for list_directory_with_sizes
```json
{
  "path": "data/sample.txt",
  "sortBy": "size"
}
```
