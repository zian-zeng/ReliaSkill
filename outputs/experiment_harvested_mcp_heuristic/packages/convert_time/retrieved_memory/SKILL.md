# convert_time

**Condition:** `retrieved_memory`

## Summary
Convert time between timezones

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

## Arguments
- `source_timezone`, string, required: Source IANA timezone name (e.g., 'America/New_York', 'Europe/London'). Use '<local_tz>' as local timezone if no source timezone provided by the user.
- `time`, string, required: Time to convert in 24-hour format (HH:MM)
- `target_timezone`, string, required: Target IANA timezone name (e.g., 'Asia/Tokyo', 'America/San_Francisco'). Use '<local_tz>' as local timezone if no target timezone provided by the user.

## Argument template
```json
{
  "source_timezone": "America/New_York",
  "time": "sample_time_1",
  "target_timezone": "America/New_York"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid memory-backed call for convert_time
```json
{
  "source_timezone": "America/New_York",
  "time": "sample_time_1",
  "target_timezone": "America/New_York"
}
```
