# create_event

**Condition:** `schema_only`

## Summary
Create a calendar event with a structured time range and optional attendees.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

## Arguments
- `title`, string, required: Short event title.
- `time_range`, object, required: When the event starts and ends.
- `visibility`, string, optional, enum=['private', 'team', 'public'], default='team': Who can view the event.
- `attendees`, array, optional: Optional attendee email addresses.
- `notes`, string, optional, nullable: Optional meeting notes.

## Argument template
```json
{
  "title": "Sample Title",
  "time_range": {
    "start": "2026-01-01T09:00:00Z",
    "end": "2026-01-01T09:00:00Z"
  },
  "visibility": "team",
  "attendees": [
    "sample_attendees_item_1"
  ],
  "notes": "sample_notes_1"
}
```

## Examples
- Minimal valid call for create_event
```json
{
  "title": "Sample Title",
  "time_range": {
    "start": "2026-01-01T09:00:00Z",
    "end": "2026-01-01T09:00:00Z"
  }
}
```
- Schema-aligned full call for create_event
```json
{
  "title": "Sample Title",
  "time_range": {
    "start": "2026-01-01T09:00:00Z",
    "end": "2026-01-01T09:00:00Z"
  },
  "visibility": "team",
  "attendees": [
    "sample_attendees_item_2"
  ],
  "notes": "sample_notes_2"
}
```
