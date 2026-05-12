# mock_system_admin_mock_query_logs_006

**Condition:** `multi_candidate_skill`

## Summary
Synthetic safe mock system-admin retrieval tool for querying offline service logs. Provide the required field `service_name`.

## When to use
- Use `mock_system_admin_mock_query_logs_006` when the user's request directly matches this tool's purpose.
- Provide the required field `service_name`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `level`: 'info', 'warning', 'error'.
- Do not use when required inputs are missing.

## Arguments
- `service_name`, string, required: Mock service name.
- `level`, string, optional, enum=['info', 'warning', 'error']: Log level.
- `window_minutes`, integer, optional: Lookback window.

## Argument template
```json
{
  "service_name": "sample-name",
  "level": "info",
  "window_minutes": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for mock_system_admin_mock_query_logs_006
```json
{
  "service_name": "sample-name"
}
```
- Richer invocation that uses optional controls for mock_system_admin_mock_query_logs_006
```json
{
  "service_name": "sample-name",
  "level": "warning",
  "window_minutes": 2
}
```
