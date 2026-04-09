# get_current_time

**Condition:** `raw_mcp`

## Summary
Get current time in a specific timezones

## When to use
- Use the original MCP description and schema directly without added guidance.
- Consult schema.normalized.json for the exact argument contract.

## When not to use
- Do not assume example calls or usage heuristics beyond the original schema.

## Arguments
- `timezone`, string, required: IANA timezone name (e.g., 'America/New_York', 'Europe/London'). Use '<local_tz>' as local timezone if no timezone provided by the user.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Semantic hints
No explicit semantic hints for this condition.

## Examples
No synthesized examples for this condition.
