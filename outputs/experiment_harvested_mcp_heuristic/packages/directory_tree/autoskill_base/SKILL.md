# directory_tree

**Condition:** `autoskill_base`

## Summary
Get a recursive tree view of files and directories as a JSON structure. Each entry includes 'name', 'type' (file/directory), and 'children' for directories. Files have no children array, while directories always have a children array (which may be empty). The output is formatted with 2-space indentation for readability. Only works within allowed directories. Provide all required fields: `path`, and `excludePatterns`.

## When to use
- Use `directory_tree` when the user's request directly matches this tool's purpose.
- Provide all required fields: `path`, and `excludePatterns`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
```json
{
  "excludePatterns": {
    "exclude": "__paths__",
    "ignore": "__paths__",
    "skip": "__paths__"
  }
}
```

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
