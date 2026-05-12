# mock_issue_tracking_create_ticket_003

**Condition:** `multi_candidate_skill`

## Summary
Synthetic safe mock issue-tracking tool that creates a ticket in an offline benchmark fixture. Provide all required fields: `project_key`, and `title`.

## When to use
- Use `mock_issue_tracking_create_ticket_003` when the user's request directly matches this tool's purpose.
- Provide all required fields: `project_key`, and `title`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `priority`: 'low', 'medium', 'high'.
- Do not use when required inputs are missing.

## Arguments
- `project_key`, string, required: Mock project key.
- `title`, string, required: Ticket title.
- `priority`, string, optional, enum=['low', 'medium', 'high']: Ticket priority.
- `labels`, array, optional: Labels to attach.
- `dry_run`, boolean, optional: When true, validate the request without changing the mock system.

## Argument template
```json
{
  "project_key": "sample_project_key_1",
  "title": "Sample Title",
  "priority": "low",
  "labels": [
    "sample_labels_item_1"
  ],
  "dry_run": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for mock_issue_tracking_create_ticket_003
```json
{
  "project_key": "sample_project_key_1",
  "title": "Sample Title"
}
```
- Richer invocation that uses optional controls for mock_issue_tracking_create_ticket_003
```json
{
  "project_key": "sample_project_key_2",
  "title": "Sample Title",
  "priority": "medium",
  "labels": [
    "sample_labels_item_2"
  ],
  "dry_run": true
}
```
