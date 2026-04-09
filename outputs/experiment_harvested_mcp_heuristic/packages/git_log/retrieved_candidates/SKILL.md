# git_log

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `git_log` over nearby tools using cues like git_log, logs, max_count, start_timestamp.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `git_log` when the request matches its role.
- Shortlist: git_log, git_branch, git_diff_staged.
- Shows the commit logs
- Shows the commit logs

## When not to use
- Do not confuse `git_log` with `git_branch`: List Git branches
- Do not confuse `git_log` with `git_diff_staged`: Shows changes that are staged for commit

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
- Minimal routed call for git_log
```json
{
  "repo_path": "data/sample.txt"
}
```
- Full routed call for git_log
```json
{
  "repo_path": "data/sample.txt",
  "max_count": 2,
  "start_timestamp": "sample_start_timestamp_2",
  "end_timestamp": "sample_end_timestamp_2"
}
```
