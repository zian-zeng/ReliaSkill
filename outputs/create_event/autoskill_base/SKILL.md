# create_event

**Condition:** `autoskill_base`

## Summary
Create a calendar event with a structured time range and optional attendees. Provide all required fields: `title`, and `time_range`.

## When to use
- Use `create_event` when the user's request directly matches this tool's purpose.
- Provide all required fields: `title`, and `time_range`.
- Optional controls include `visibility`, `attendees`, `notes`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `visibility`: 'private', 'team', 'public'.
- Schema forbids unknown top-level arguments.

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
- Minimal valid request that satisfies the required fields for create_event
```json
{
  "title": "Sample Title",
  "time_range": {
    "start": "2026-01-01T09:00:00Z",
    "end": "2026-01-01T09:00:00Z"
  }
}
```
- Richer invocation that uses optional controls for create_event
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
