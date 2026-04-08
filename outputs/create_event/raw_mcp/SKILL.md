# create_event

**Condition:** `raw_mcp`

## Summary
Create a calendar event with a structured time range and optional attendees.

## When to use
- Use the original MCP description and schema directly without added guidance.
- Consult schema.normalized.json for the exact argument contract.

## When not to use
- Do not assume example calls or usage heuristics beyond the original schema.

## Arguments
- `title`, string, required: Short event title.
- `time_range`, object, required: When the event starts and ends.
- `visibility`, string, optional, enum=['private', 'team', 'public'], default='team': Who can view the event.
- `attendees`, array, optional: Optional attendee email addresses.
- `notes`, string, optional, nullable: Optional meeting notes.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Examples
No synthesized examples for this condition.
