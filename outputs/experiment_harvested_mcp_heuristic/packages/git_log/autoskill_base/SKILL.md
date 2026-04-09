# git_log

**Condition:** `autoskill_base`

## Summary
Shows the commit logs. Provide the required field `repo_path`.

## When to use
- Use `git_log` when the user's request directly matches this tool's purpose.
- Provide the required field `repo_path`.
- Optional controls include `max_count`, `start_timestamp`, `end_timestamp`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
- Minimal valid request that satisfies the required fields for git_log
```json
{
  "repo_path": "data/sample.txt"
}
```
- Richer invocation that uses optional controls for git_log
```json
{
  "repo_path": "data/sample.txt",
  "max_count": 2,
  "start_timestamp": "sample_start_timestamp_2",
  "end_timestamp": "sample_end_timestamp_2"
}
```
