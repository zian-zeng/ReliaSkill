# edit_file

**Condition:** `retrieved_memory`

## Summary
Make line-based edits to a text file. Each edit replaces exact line sequences with new content. Returns a git-style diff showing the changes made. Only works within allowed directories.

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `path`, string, required: No description provided.
- `edits`, array, required: No description provided.
- `dryRun`, boolean, required: No description provided.

## Argument template
```json
{
  "path": "data/sample.txt",
  "edits": [
    {}
  ],
  "dryRun": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for edit_file
```json
{
  "path": "data/sample.txt",
  "edits": [
    {}
  ],
  "dryRun": false
}
```
