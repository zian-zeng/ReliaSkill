# notes_create_memory

**Condition:** `multi_candidate_skill`

## Summary
API-Bank-style local fixture tool for saving a note to an offline memory store. Provide all required fields: `workspace`, `title`, and `content`.

## When to use
- Use `notes_create_memory` when the user's request directly matches this tool's purpose.
- Provide all required fields: `workspace`, `title`, and `content`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `workspace`, string, required: Mock workspace.
- `title`, string, required: Note title.
- `content`, string, required: Note content.
- `tags`, array, optional: Note tags.

## Argument template
```json
{
  "workspace": "sample_workspace_1",
  "title": "Sample Title",
  "content": "sample_content_1",
  "tags": [
    "sample_tags_item_1"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for notes_create_memory
```json
{
  "workspace": "sample_workspace_1",
  "title": "Sample Title",
  "content": "sample_content_1"
}
```
- Richer invocation that uses optional controls for notes_create_memory
```json
{
  "workspace": "sample_workspace_2",
  "title": "Sample Title",
  "content": "sample_content_2",
  "tags": [
    "sample_tags_item_2"
  ]
}
```
