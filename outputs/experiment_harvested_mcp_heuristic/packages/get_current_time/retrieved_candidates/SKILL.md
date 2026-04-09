# get_current_time

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `get_current_time` over nearby tools using cues like get_current_time, current, specific.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `get_current_time` when the request matches its role.
- Shortlist: get_current_time, convert_time, directory_tree.
- Get current time in a specific timezones
- Get current time in a specific timezones

## When not to use
- Do not confuse `get_current_time` with `convert_time`: Convert time between timezones
- Do not confuse `get_current_time` with `directory_tree`: Get a recursive tree view of files and directories as a JSON structure. Each entry includes 'name', 'type' (file/directory), and 'children' for directories. Files have no children array, while directories always have a children array (which may be empty). The output is formatted with 2-space indentation for readability. Only works within allowed directories.

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
- Minimal routed call for get_current_time
```json
{
  "timezone": "America/New_York"
}
```
