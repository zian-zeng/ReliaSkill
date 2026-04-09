# directory_tree

**Condition:** `retrieved_docs`

## Summary
Get a recursive tree view of files and directories as a JSON structure. Each entry includes 'name', 'type' (file/directory), and 'children' for directories. Files have no children array, while directories always have a children array (which may be empty). The output is formatted with 2-space indentation for readability. Only works within allowed directories. Directory Tree

## When to use
- Get a recursive tree view of files and directories as a JSON structure. Each entry includes 'name', 'type' (file/directory), and 'children' for directories. Files have no children array, while directories always have a children array (which may be empty). The output is formatted with 2-space indentation for readability. Only works within allowed directories.
- Directory Tree
- excludePatterns required
- path required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for directory_tree
```json
{
  "path": "data/sample.txt",
  "excludePatterns": [
    "sample_excludePatterns_item_1"
  ]
}
```
- Retrieved-docs fuller call for directory_tree
```json
{
  "path": "data/sample.txt",
  "excludePatterns": [
    "sample_excludePatterns_item_2"
  ]
}
```
