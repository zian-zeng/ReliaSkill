# echo

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `echo` over nearby tools using cues like echo, echoes, back, string.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `echo` when the request matches its role.
- Shortlist: echo, list_allowed_directories, read_graph.
- Echoes back the input string
- Echoes back the input string

## When not to use
- Do not confuse `echo` with `list_allowed_directories`: Returns the list of directories that this server is allowed to access. Subdirectories within these allowed directories are also accessible. Use this to understand which directories and their nested paths are available before trying to access files.
- Do not confuse `echo` with `read_graph`: Read the entire knowledge graph

## Arguments
- `message`, string, required: No description provided.

## Argument template
```json
{
  "message": "sample_message_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for echo
```json
{
  "message": "sample_message_1"
}
```
- Full routed call for echo
```json
{
  "message": "sample_message_2"
}
```
