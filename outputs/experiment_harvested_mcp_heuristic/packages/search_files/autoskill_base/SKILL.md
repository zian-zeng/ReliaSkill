# search_files

**Condition:** `autoskill_base`

## Summary
Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you don't know their exact location. Only searches within allowed directories. Provide all required fields: `path`, `pattern`, and `excludePatterns`.

## When to use
- Use `search_files` when the user's request directly matches this tool's purpose.
- Provide all required fields: `path`, `pattern`, and `excludePatterns`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
```json
{
  "pattern": {
    "python": "**/*.py",
    "markdown": "**/*.md",
    "text": "**/*.txt",
    "json": "**/*.json",
    "yaml": "**/*.yaml",
    "yml": "**/*.yml"
  },
  "excludePatterns": {
    "exclude": "__paths__",
    "ignore": "__paths__",
    "skip": "__paths__"
  }
}
```

## Examples
- Minimal valid request that satisfies the required fields for search_files
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_1",
  "excludePatterns": [
    "sample_excludePatterns_item_1"
  ]
}
```
- Richer invocation that uses optional controls for search_files
```json
{
  "path": "data/sample.txt",
  "pattern": "sample_pattern_2",
  "excludePatterns": [
    "sample_excludePatterns_item_2"
  ]
}
```
- Semantic cue for Python files
```json
{
  "path": "src",
  "pattern": "**/*.py",
  "excludePatterns": []
}
```
- Semantic cue for Markdown files
```json
{
  "path": "docs",
  "pattern": "**/*.md",
  "excludePatterns": []
}
```
