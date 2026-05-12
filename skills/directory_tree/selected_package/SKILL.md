# directory_tree

**Condition:** `multi_candidate_skill`

## Summary
Get a recursive tree view of files and directories as a JSON structure. Each entry includes 'name', 'type' (file/directory), and 'children' for directories. Files have no children array, while directories always have a children array (which may be empty). The.

## When to use
- Use `directory_tree` when the user's request directly matches this tool's purpose.
- Provide all required fields: `path`, and `excludePatterns`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

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
- Minimal valid request that satisfies the required fields for directory_tree
```json
{
  "path": "data/sample.txt",
  "excludePatterns": [
    "sample_excludePatterns_item_1"
  ]
}
```
- Richer invocation that uses optional controls for directory_tree
```json
{
  "path": "data/sample.txt",
  "excludePatterns": [
    "sample_excludePatterns_item_2"
  ]
}
```
