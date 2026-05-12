# calendar_find_free_slots

**Condition:** `multi_candidate_skill`

## Summary
API-Bank-style local fixture retrieval tool for finding free slots across calendars. Provide all required fields: `calendar_ids`, `duration_minutes`, and `window`.

## When to use
- Use `calendar_find_free_slots` when the user's request directly matches this tool's purpose.
- Provide all required fields: `calendar_ids`, `duration_minutes`, and `window`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `calendar_ids`, array, required: Calendars to inspect.
- `duration_minutes`, integer, required: Required slot duration.
- `window`, object, required: Search window.

## Argument template
```json
{
  "calendar_ids": [
    "sample_calendar_ids_item_1"
  ],
  "duration_minutes": 1,
  "window": {
    "end": "2026-01-01T09:00:00Z",
    "start": "2026-01-01T09:00:00Z"
  }
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calendar_find_free_slots
```json
{
  "calendar_ids": [
    "sample_calendar_ids_item_1"
  ],
  "duration_minutes": 1,
  "window": {
    "end": "2026-01-01T09:00:00Z",
    "start": "2026-01-01T09:00:00Z"
  }
}
```
- Richer invocation that uses optional controls for calendar_find_free_slots
```json
{
  "calendar_ids": [
    "sample_calendar_ids_item_2"
  ],
  "duration_minutes": 2,
  "window": {
    "end": "2026-01-01T09:00:00Z",
    "start": "2026-01-01T09:00:00Z"
  }
}
```
