# edit_file

**Condition:** `schema_only`

## Summary
Make line-based edits to a text file. Each edit replaces exact line sequences with new content. Returns a git-style diff showing the changes made. Only works within allowed directories.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for edit_file
```json
{
  "path": "data/sample.txt",
  "edits": [
    {}
  ],
  "dryRun": false
}
```
- Schema-aligned full call for edit_file
```json
{
  "path": "data/sample.txt",
  "edits": [
    {}
  ],
  "dryRun": true
}
```
