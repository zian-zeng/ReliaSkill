# get_current_time

**Condition:** `retrieved_docs`

## Summary
timezone required IANA timezone name (e.g., 'America/New_York', 'Europe/London'). Use '<local_tz>' as local timezone if no timezone provided by the user. Get current time in a specific timezones

## When to use
- timezone required IANA timezone name (e.g., 'America/New_York', 'Europe/London'). Use '<local_tz>' as local timezone if no timezone provided by the user.
- Get current time in a specific timezones
- get_current_time

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for get_current_time
```json
{
  "timezone": "America/New_York"
}
```
