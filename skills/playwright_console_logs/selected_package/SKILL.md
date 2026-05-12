# playwright_console_logs

**Condition:** `multi_candidate_skill`

## Summary
Retrieve console logs from the browser with filtering options. This tool has no required input fields.

## When to use
- Use `playwright_console_logs` when the user's request directly matches this tool's purpose.
- This tool has no required input fields.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `type`: 'all', 'error', 'warning', 'log'.
- Do not use when required inputs are missing.

## Arguments
- `type`, string, optional, enum=['all', 'error', 'warning', 'log', 'info', 'debug', 'exception']: Type of logs to retrieve (all, error, warning, log, info, debug, exception)
- `search`, string, optional: Text to search for in logs (handles text with square brackets)
- `limit`, number, optional: Maximum number of logs to return
- `clear`, boolean, optional: Whether to clear logs after retrieval (default: false)

## Argument template
```json
{
  "type": "all",
  "search": "sample query",
  "limit": 1.0,
  "clear": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Richer invocation that uses optional controls for playwright_console_logs
```json
{
  "type": "error",
  "search": "sample query",
  "limit": 2.0,
  "clear": true
}
```
