# list_allowed_directories

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `list_allowed_directories` over nearby tools using cues like list_allowed_directories, list, this, access..

## When to use
- Retrieve a shortlist of nearby tools first, then choose `list_allowed_directories` when the request matches its role.
- Shortlist: list_allowed_directories, trigger-elicitation-request-async, search_files.
- Returns the list of directories that this server is allowed to access. Subdirectories within these allowed directories are also accessible. Use this to understand which directories and their nested paths are available before trying to access files.
- Returns the list of directories that this server is allowed to access. Subdirectories within these allowed directories are also accessible. Use this to understand which directories and their nested paths are available before trying to access files.

## When not to use
- Do not confuse `list_allowed_directories` with `trigger-elicitation-request-async`: Trigger an async elicitation request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends an elicitation request and the client handles user input asynchronously, allowing the server to poll for completion.
- Do not confuse `list_allowed_directories` with `search_files`: Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you don't know their exact location. Only searches within allowed directories.

## Arguments
- This tool does not expose structured input arguments.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Semantic hints
No explicit semantic hints for this condition.

## Examples
No synthesized examples for this condition.
