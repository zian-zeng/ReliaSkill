# get_current_time

**Condition:** `autoskill_base`

## Summary
Get current time in a specific timezones. Provide the required field `timezone`.

## When to use
- Use `get_current_time` when the user's request directly matches this tool's purpose.
- Provide the required field `timezone`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
- Minimal valid request that satisfies the required fields for get_current_time
```json
{
  "timezone": "America/New_York"
}
```
- Richer invocation that uses optional controls for get_current_time
```json
{
  "timezone": "America/New_York"
}
```
