# search_files

**Condition:** `retrieved_memory`

## Summary
Search text files and ignore an archive subtree. Find markdown files under a docs directory.

## When to use
- Retrieve similar skill examples from memory before filling arguments.
- Search text files and ignore an archive subtree.
- Find markdown files under a docs directory.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `path`, string, required: No description provided.
- `pattern`, string, required: No description provided.
- `excludePatterns`, array, required: No description provided.

## Argument template
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_1",
  "excludePatterns": [
    "sample_excludePatterns_item_1"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for search_files
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_1",
  "excludePatterns": [
    "sample_excludePatterns_item_1"
  ]
}
```
- Search text files and ignore an archive subtree.
```json
{
  "path": "logs",
  "pattern": "**/*.txt",
  "excludePatterns": [
    "logs/archive/**"
  ]
}
```
- Find markdown files under a docs directory.
```json
{
  "path": "docs",
  "pattern": "**/*.md",
  "excludePatterns": []
}
```
- Find python files under a directory.
```json
{
  "path": "src",
  "pattern": "**/*.py",
  "excludePatterns": []
}
```
