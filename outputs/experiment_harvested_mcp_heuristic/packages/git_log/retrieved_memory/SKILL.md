# git_log

**Condition:** `retrieved_memory`

## Summary
Shows the commit logs

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

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
- Minimal valid memory-backed call for git_log
```json
{
  "repo_path": "data/sample.txt"
}
```
