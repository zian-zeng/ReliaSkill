# get-env

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `get-env` over nearby tools using cues like get-env, environment, variables, helpful.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `get-env` when the request matches its role.
- Shortlist: get-env, list_allowed_directories, trigger-elicitation-request-async.
- Returns all environment variables, helpful for debugging MCP server configuration
- Returns all environment variables, helpful for debugging MCP server configuration

## When not to use
- Do not confuse `get-env` with `list_allowed_directories`: Returns the list of directories that this server is allowed to access. Subdirectories within these allowed directories are also accessible. Use this to understand which directories and their nested paths are available before trying to access files.
- Do not confuse `get-env` with `trigger-elicitation-request-async`: Trigger an async elicitation request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends an elicitation request and the client handles user input asynchronously, allowing the server to poll for completion.

## Arguments
- This tool does not expose structured input arguments.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Semantic hints
No explicit semantic hints for this condition.

## Examples
No synthesized examples for this condition.
