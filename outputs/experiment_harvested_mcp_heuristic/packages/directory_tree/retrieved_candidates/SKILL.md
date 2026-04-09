# directory_tree

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `directory_tree` over nearby tools using cues like directory_tree, recursive, tree, view.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `directory_tree` when the request matches its role.
- Shortlist: directory_tree, list_directory, list_directory_with_sizes.
- Get a recursive tree view of files and directories as a JSON structure. Each entry includes 'name', 'type' (file/directory), and 'children' for directories. Files have no children array, while directories always have a children array (which may be empty). The output is formatted with 2-space indentation for readability. Only works within allowed directories.
- Get a recursive tree view of files and directories as a JSON structure. Each entry includes 'name', 'type' (file/directory), and 'children' for directories. Files have no children array, while directories always have a children array (which may be empty). The output is formatted with 2-space indentation for readability. Only works within allowed directories.

## When not to use
- Do not confuse `directory_tree` with `list_directory`: Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory. Only works within allowed directories.
- Do not confuse `directory_tree` with `list_directory_with_sizes`: Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within a directory. Only works within allowed directories.

## Arguments
- `path`, string, required: No description provided.
- `excludePatterns`, array, required: No description provided.

## Argument template
```json
{
  "path": "data/sample.txt",
  "excludePatterns": [
    "sample_excludePatterns_item_1"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for directory_tree
```json
{
  "path": "data/sample.txt",
  "excludePatterns": [
    "sample_excludePatterns_item_1"
  ]
}
```
- Full routed call for directory_tree
```json
{
  "path": "data/sample.txt",
  "excludePatterns": [
    "sample_excludePatterns_item_2"
  ]
}
```
