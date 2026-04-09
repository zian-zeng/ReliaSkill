# git_log

**Condition:** `schema_only`

## Summary
Shows the commit logs

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for git_log
```json
{
  "repo_path": "data/sample.txt"
}
```
- Schema-aligned full call for git_log
```json
{
  "repo_path": "data/sample.txt",
  "max_count": 2,
  "start_timestamp": "sample_start_timestamp_2",
  "end_timestamp": "sample_end_timestamp_2"
}
```
