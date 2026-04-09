# read_graph

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `read_graph` over nearby tools using cues like read_graph, read, entire, knowledge.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `read_graph` when the request matches its role.
- Shortlist: read_graph, list_allowed_directories, trigger-elicitation-request.
- Read the entire knowledge graph
- Read the entire knowledge graph

## When not to use
- Do not confuse `read_graph` with `list_allowed_directories`: Returns the list of directories that this server is allowed to access. Subdirectories within these allowed directories are also accessible. Use this to understand which directories and their nested paths are available before trying to access files.
- Do not confuse `read_graph` with `trigger-elicitation-request`: Trigger a Request from the Server for User Elicitation

## Arguments
- This tool does not expose structured input arguments.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Semantic hints
No explicit semantic hints for this condition.

## Examples
No synthesized examples for this condition.
