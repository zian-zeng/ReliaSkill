# mock_issue_tracking_search_tickets_039

**Condition:** `multi_candidate_skill`

## Summary
Synthetic safe mock issue-tracking retrieval tool for searching offline tickets by status and assignee. Provide the required field `query`.

## When to use
- Use `mock_issue_tracking_search_tickets_039` when the user's request directly matches this tool's purpose.
- Provide the required field `query`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `status`: 'open', 'blocked', 'closed'.
- Do not use when required inputs are missing.

## Arguments
- `query`, string, required: Search text.
- `status`, string, optional, enum=['open', 'blocked', 'closed']: Ticket status.
- `assignee`, string, optional: Mock assignee username.

## Argument template
```json
{
  "query": "sample query",
  "status": "open",
  "assignee": "sample_assignee_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for mock_issue_tracking_search_tickets_039
```json
{
  "query": "sample query"
}
```
- Richer invocation that uses optional controls for mock_issue_tracking_search_tickets_039
```json
{
  "query": "sample query",
  "status": "blocked",
  "assignee": "sample_assignee_2"
}
```
