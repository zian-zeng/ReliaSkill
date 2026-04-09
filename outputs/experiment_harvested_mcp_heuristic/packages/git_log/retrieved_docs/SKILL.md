# git_log

**Condition:** `retrieved_docs`

## Summary
start_timestamp optional Start timestamp for filtering commits. Accepts: ISO 8601 format (e.g., '2024-01-15T14:30:25'), relative dates (e.g., '2 weeks ago', 'yesterday'), or absolute dates (e.g., '2024-01-15', 'Jan 15 2024') end_timestamp optional End timestamp for filtering commits. Accepts: ISO 8601 format (e.g., '2024-01-15T14:30:25'), relative dates (e.g., '2 weeks ago', 'yesterday'), or absolute dates (e.g., '2024-01-15', 'Jan 15 2024')

## When to use
- start_timestamp optional Start timestamp for filtering commits. Accepts: ISO 8601 format (e.g., '2024-01-15T14:30:25'), relative dates (e.g., '2 weeks ago', 'yesterday'), or absolute dates (e.g., '2024-01-15', 'Jan 15 2024')
- end_timestamp optional End timestamp for filtering commits. Accepts: ISO 8601 format (e.g., '2024-01-15T14:30:25'), relative dates (e.g., '2 weeks ago', 'yesterday'), or absolute dates (e.g., '2024-01-15', 'Jan 15 2024')
- Shows the commit logs
- git_log

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

## Arguments
- `repo_path`, string, required: No description provided.
- `max_count`, integer, optional: No description provided.
- `start_timestamp`, string, optional: Start timestamp for filtering commits. Accepts: ISO 8601 format (e.g., '2024-01-15T14:30:25'), relative dates (e.g., '2 weeks ago', 'yesterday'), or absolute dates (e.g., '2024-01-15', 'Jan 15 2024')
- `end_timestamp`, string, optional: End timestamp for filtering commits. Accepts: ISO 8601 format (e.g., '2024-01-15T14:30:25'), relative dates (e.g., '2 weeks ago', 'yesterday'), or absolute dates (e.g., '2024-01-15', 'Jan 15 2024')

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "max_count": 1,
  "start_timestamp": "sample_start_timestamp_1",
  "end_timestamp": "sample_end_timestamp_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Retrieved-docs minimal call for git_log
```json
{
  "repo_path": "data/sample.txt"
}
```
- Retrieved-docs fuller call for git_log
```json
{
  "repo_path": "data/sample.txt",
  "max_count": 2,
  "start_timestamp": "sample_start_timestamp_2",
  "end_timestamp": "sample_end_timestamp_2"
}
```
