# convert_time

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `convert_time` over nearby tools using cues like convert_time, convert, between, source_timezone.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `convert_time` when the request matches its role.
- Shortlist: convert_time, get_current_time, git_branch.
- Convert time between timezones
- Convert time between timezones

## When not to use
- Do not confuse `convert_time` with `get_current_time`: Get current time in a specific timezones
- Do not confuse `convert_time` with `git_branch`: List Git branches

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
- Minimal routed call for convert_time
```json
{
  "source_timezone": "America/New_York",
  "time": "sample_time_1",
  "target_timezone": "America/New_York"
}
```
- Full routed call for convert_time
```json
{
  "source_timezone": "America/New_York",
  "time": "sample_time_2",
  "target_timezone": "America/New_York"
}
```
