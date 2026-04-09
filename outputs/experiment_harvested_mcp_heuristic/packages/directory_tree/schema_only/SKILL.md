# directory_tree

**Condition:** `schema_only`

## Summary
Get a recursive tree view of files and directories as a JSON structure. Each entry includes 'name', 'type' (file/directory), and 'children' for directories. Files have no children array, while directories always have a children array (which may be empty). The output is formatted with 2-space indentation for readability. Only works within allowed directories.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for directory_tree
```json
{
  "path": "data/sample.txt",
  "excludePatterns": [
    "sample_excludePatterns_item_1"
  ]
}
```
- Schema-aligned full call for directory_tree
```json
{
  "path": "data/sample.txt",
  "excludePatterns": [
    "sample_excludePatterns_item_2"
  ]
}
```
