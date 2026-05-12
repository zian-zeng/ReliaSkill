# mock_messaging_email_mock_search_mail_005

**Condition:** `multi_candidate_skill`

## Summary
Synthetic safe mock mailbox search tool over local fixture messages. Provide the required field `query`.

## When to use
- Use `mock_messaging_email_mock_search_mail_005` when the user's request directly matches this tool's purpose.
- Provide the required field `query`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `folder`: 'inbox', 'sent', 'archive'.
- Do not use when required inputs are missing.

## Arguments
- `query`, string, required: Mailbox search query.
- `folder`, string, optional, enum=['inbox', 'sent', 'archive']: Mailbox folder.
- `limit`, integer, optional: Maximum mock messages to return.

## Argument template
```json
{
  "query": "sample query",
  "folder": "inbox",
  "limit": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for mock_messaging_email_mock_search_mail_005
```json
{
  "query": "sample query"
}
```
- Richer invocation that uses optional controls for mock_messaging_email_mock_search_mail_005
```json
{
  "query": "sample query",
  "folder": "sent",
  "limit": 2
}
```
