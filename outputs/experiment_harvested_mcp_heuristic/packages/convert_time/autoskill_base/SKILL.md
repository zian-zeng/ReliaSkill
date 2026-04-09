# convert_time

**Condition:** `autoskill_base`

## Summary
Convert time between timezones. Provide all required fields: `source_timezone`, `time`, and `target_timezone`.

## When to use
- Use `convert_time` when the user's request directly matches this tool's purpose.
- Provide all required fields: `source_timezone`, `time`, and `target_timezone`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
- Minimal valid request that satisfies the required fields for convert_time
```json
{
  "source_timezone": "America/New_York",
  "time": "sample_time_1",
  "target_timezone": "America/New_York"
}
```
- Richer invocation that uses optional controls for convert_time
```json
{
  "source_timezone": "America/New_York",
  "time": "sample_time_2",
  "target_timezone": "America/New_York"
}
```
