# calendar_create_event

**Condition:** `multi_candidate_skill`

## Summary
API-Bank-style local fixture tool that creates a mock calendar event with attendees and reminders. Provide all required fields: `calendar_id`, `title`, `start_time`, and `end_time`.

## When to use
- Use `calendar_create_event` when the user's request directly matches this tool's purpose.
- Provide all required fields: `calendar_id`, `title`, `start_time`, and `end_time`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `visibility`: 'default', 'private', 'public'.
- Do not use when required inputs are missing.

## Arguments
- `calendar_id`, string, required: Mock calendar identifier.
- `title`, string, required: Event title.
- `start_time`, string, required, format=date-time: Event start time.
- `end_time`, string, required, format=date-time: Event end time.
- `attendees`, array, optional: Attendee email addresses.
- `visibility`, string, optional, enum=['default', 'private', 'public']: Event visibility.

## Argument template
```json
{
  "calendar_id": "sample-calendar-id-001",
  "title": "Sample Title",
  "start_time": "2026-01-01T09:00:00Z",
  "end_time": "2026-01-01T09:00:00Z",
  "attendees": [
    "sample_attendees_item_1"
  ],
  "visibility": "default"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calendar_create_event
```json
{
  "calendar_id": "sample-calendar-id-001",
  "title": "Sample Title",
  "start_time": "2026-01-01T09:00:00Z",
  "end_time": "2026-01-01T09:00:00Z"
}
```
- Richer invocation that uses optional controls for calendar_create_event
```json
{
  "calendar_id": "sample-calendar-id-001",
  "title": "Sample Title",
  "start_time": "2026-01-01T09:00:00Z",
  "end_time": "2026-01-01T09:00:00Z",
  "attendees": [
    "sample_attendees_item_2"
  ],
  "visibility": "private"
}
```
