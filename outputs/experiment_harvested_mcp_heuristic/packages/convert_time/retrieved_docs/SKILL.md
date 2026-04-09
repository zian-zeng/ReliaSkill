# convert_time

**Condition:** `retrieved_docs`

## Summary
target_timezone required Target IANA timezone name (e.g., 'Asia/Tokyo', 'America/San_Francisco'). Use '<local_tz>' as local timezone if no target timezone provided by the user. source_timezone required Source IANA timezone name (e.g., 'America/New_York', 'Europe/London'). Use '<local_tz>' as local timezone if no source timezone provided by the user.

## When to use
- target_timezone required Target IANA timezone name (e.g., 'Asia/Tokyo', 'America/San_Francisco'). Use '<local_tz>' as local timezone if no target timezone provided by the user.
- source_timezone required Source IANA timezone name (e.g., 'America/New_York', 'Europe/London'). Use '<local_tz>' as local timezone if no source timezone provided by the user.
- time required Time to convert in 24-hour format (HH:MM)
- Convert time between timezones

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for convert_time
```json
{
  "source_timezone": "America/New_York",
  "time": "sample_time_1",
  "target_timezone": "America/New_York"
}
```
- Retrieved-docs fuller call for convert_time
```json
{
  "source_timezone": "America/New_York",
  "time": "sample_time_2",
  "target_timezone": "America/New_York"
}
```
