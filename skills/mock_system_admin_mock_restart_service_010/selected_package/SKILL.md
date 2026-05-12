# mock_system_admin_mock_restart_service_010

**Condition:** `multi_candidate_skill`

## Summary
Synthetic safe mock system-admin tool that simulates a service restart in an offline fixture. Provide all required fields: `service_name`, `environment`, and `reason`.

## When to use
- Use `mock_system_admin_mock_restart_service_010` when the user's request directly matches this tool's purpose.
- Provide all required fields: `service_name`, `environment`, and `reason`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `environment`: 'dev', 'staging'.
- Do not use when required inputs are missing.

## Arguments
- `service_name`, string, required: Mock service name.
- `environment`, string, required, enum=['dev', 'staging']: Allowed mock environment.
- `reason`, string, required: Operational reason.
- `dry_run`, boolean, optional: When true, validate the request without changing the mock system.

## Argument template
```json
{
  "service_name": "sample-name",
  "environment": "dev",
  "reason": "sample_reason_1",
  "dry_run": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for mock_system_admin_mock_restart_service_010
```json
{
  "service_name": "sample-name",
  "environment": "dev",
  "reason": "sample_reason_1"
}
```
- Richer invocation that uses optional controls for mock_system_admin_mock_restart_service_010
```json
{
  "service_name": "sample-name",
  "environment": "staging",
  "reason": "sample_reason_2",
  "dry_run": true
}
```
