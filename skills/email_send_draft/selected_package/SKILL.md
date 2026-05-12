# email_send_draft

**Condition:** `multi_candidate_skill`

## Summary
API-Bank-style local fixture tool that marks a mock email draft as sent without using a real network service. Provide the required field `draft_id`.

## When to use
- Use `email_send_draft` when the user's request directly matches this tool's purpose.
- Provide the required field `draft_id`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `draft_id`, string, required: Mock draft identifier.
- `send_at`, string, optional, format=date-time: Optional scheduled send time.
- `dry_run`, boolean, optional: Validate without marking sent.

## Argument template
```json
{
  "draft_id": "sample-draft-id-001",
  "send_at": "2026-01-01T09:00:00Z",
  "dry_run": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for email_send_draft
```json
{
  "draft_id": "sample-draft-id-001"
}
```
- Richer invocation that uses optional controls for email_send_draft
```json
{
  "draft_id": "sample-draft-id-001",
  "send_at": "2026-01-01T09:00:00Z",
  "dry_run": true
}
```
