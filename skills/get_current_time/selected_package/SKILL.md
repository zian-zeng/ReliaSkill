# get_current_time

**Condition:** `multi_candidate_skill`

## Summary
Get current time in a specific timezones. Provide the required field `timezone`.

## When to use
- Use `get_current_time` when the user's request directly matches this tool's purpose.
- Provide the required field `timezone`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

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
- Required-argument dev behavior example.
```json
{
  "timezone": "America/New_York"
}
```
