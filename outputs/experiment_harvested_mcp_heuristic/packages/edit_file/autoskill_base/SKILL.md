# edit_file

**Condition:** `autoskill_base`

## Summary
Make line-based edits to a text file. Each edit replaces exact line sequences with new content. Returns a git-style diff showing the changes made. Only works within allowed directories. Provide all required fields: `path`, `edits`, and `dryRun`.

## When to use
- Use `edit_file` when the user's request directly matches this tool's purpose.
- Provide all required fields: `path`, `edits`, and `dryRun`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
- Minimal valid request that satisfies the required fields for edit_file
```json
{
  "path": "data/sample.txt",
  "edits": [
    {}
  ],
  "dryRun": false
}
```
- Richer invocation that uses optional controls for edit_file
```json
{
  "path": "data/sample.txt",
  "edits": [
    {}
  ],
  "dryRun": true
}
```
