# mock_messaging_email_mock_send_email_001

**Condition:** `multi_candidate_skill`

## Summary
Synthetic safe mock email tool that records an outbound message without contacting any external service. Provide all required fields: `to`, `subject`, and `body`.

## When to use
- Use `mock_messaging_email_mock_send_email_001` when the user's request directly matches this tool's purpose.
- Provide all required fields: `to`, `subject`, and `body`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `importance`: 'normal', 'high'.
- Do not use when required inputs are missing.

## Arguments
- `to`, array, required: Recipient email addresses.
- `subject`, string, required: Message subject.
- `body`, string, required: Message body.
- `importance`, string, optional, enum=['normal', 'high']: Mock importance flag.
- `dry_run`, boolean, optional: When true, validate the request without changing the mock system.

## Argument template
```json
{
  "to": [
    "sample_to_item_1"
  ],
  "subject": "sample_subject_1",
  "body": "sample_body_1",
  "importance": "normal",
  "dry_run": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for mock_messaging_email_mock_send_email_001
```json
{
  "to": [
    "sample_to_item_1"
  ],
  "subject": "sample_subject_1",
  "body": "sample_body_1"
}
```
- Richer invocation that uses optional controls for mock_messaging_email_mock_send_email_001
```json
{
  "to": [
    "sample_to_item_2"
  ],
  "subject": "sample_subject_2",
  "body": "sample_body_2",
  "importance": "high",
  "dry_run": true
}
```
