# convert_time

**Condition:** `raw_mcp`

## Summary
Convert time between timezones

## When to use
- Use the original MCP description and schema directly without added guidance.
- Consult schema.normalized.json for the exact argument contract.

## When not to use
- Do not assume example calls or usage heuristics beyond the original schema.

## Arguments
- `source_timezone`, string, required: Source IANA timezone name (e.g., 'America/New_York', 'Europe/London'). Use '<local_tz>' as local timezone if no source timezone provided by the user.
- `time`, string, required: Time to convert in 24-hour format (HH:MM)
- `target_timezone`, string, required: Target IANA timezone name (e.g., 'Asia/Tokyo', 'America/San_Francisco'). Use '<local_tz>' as local timezone if no target timezone provided by the user.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Semantic hints
No explicit semantic hints for this condition.

## Examples
No synthesized examples for this condition.
