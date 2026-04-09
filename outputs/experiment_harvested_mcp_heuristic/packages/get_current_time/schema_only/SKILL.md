# get_current_time

**Condition:** `schema_only`

## Summary
Get current time in a specific timezones

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

## Arguments
- `timezone`, string, required: IANA timezone name (e.g., 'America/New_York', 'Europe/London'). Use '<local_tz>' as local timezone if no timezone provided by the user.

## Argument template
```json
{
  "timezone": "America/New_York"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid call for get_current_time
```json
{
  "timezone": "America/New_York"
}
```
