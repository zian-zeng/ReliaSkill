# email_draft_message

**Condition:** `multi_candidate_skill`

## Summary
API-Bank-style local fixture tool that creates a draft email in an offline mailbox fixture. Provide all required fields: `to`, `subject`, and `body`.

## When to use
- Use `email_draft_message` when the user's request directly matches this tool's purpose.
- Provide all required fields: `to`, `subject`, and `body`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `to`, array, required: Recipients.
- `subject`, string, required: Draft subject.
- `body`, string, required: Draft body.
- `cc`, array, optional: Optional cc recipients.

## Argument template
```json
{
  "to": [
    "sample_to_item_1"
  ],
  "subject": "sample_subject_1",
  "body": "sample_body_1",
  "cc": [
    "sample_cc_item_1"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for email_draft_message
```json
{
  "to": [
    "sample_to_item_1"
  ],
  "subject": "sample_subject_1",
  "body": "sample_body_1"
}
```
- Richer invocation that uses optional controls for email_draft_message
```json
{
  "to": [
    "sample_to_item_2"
  ],
  "subject": "sample_subject_2",
  "body": "sample_body_2",
  "cc": [
    "sample_cc_item_2"
  ]
}
```
