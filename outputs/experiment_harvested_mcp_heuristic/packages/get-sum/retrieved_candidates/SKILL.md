# get-sum

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `get-sum` over nearby tools using cues like get-sum, numbers.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `get-sum` when the request matches its role.
- Shortlist: get-sum, get_file_info, directory_tree.
- Returns the sum of two numbers
- Returns the sum of two numbers

## When not to use
- Do not confuse `get-sum` with `get_file_info`: Retrieve detailed metadata about a file or directory. Returns comprehensive information including size, creation time, last modified time, permissions, and type. This tool is perfect for understanding file characteristics without reading the actual content. Only works within allowed directories.
- Do not confuse `get-sum` with `directory_tree`: Get a recursive tree view of files and directories as a JSON structure. Each entry includes 'name', 'type' (file/directory), and 'children' for directories. Files have no children array, while directories always have a children array (which may be empty). The output is formatted with 2-space indentation for readability. Only works within allowed directories.

## Arguments
- `a`, number, required: No description provided.
- `b`, number, required: No description provided.

## Argument template
```json
{
  "a": 1.0,
  "b": 1.0
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for get-sum
```json
{
  "a": 1.0,
  "b": 1.0
}
```
- Full routed call for get-sum
```json
{
  "a": 2.0,
  "b": 2.0
}
```
