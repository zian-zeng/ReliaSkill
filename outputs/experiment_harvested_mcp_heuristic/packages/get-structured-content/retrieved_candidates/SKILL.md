# get-structured-content

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `get-structured-content` over nearby tools using cues like get-structured-content, structured, content, along.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `get-structured-content` when the request matches its role.
- Shortlist: get-structured-content, trigger-elicitation-request-async, get-env.
- Returns structured content along with an output schema for client data validation
- Returns structured content along with an output schema for client data validation

## When not to use
- Do not confuse `get-structured-content` with `trigger-elicitation-request-async`: Trigger an async elicitation request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends an elicitation request and the client handles user input asynchronously, allowing the server to poll for completion.
- Do not confuse `get-structured-content` with `get-env`: Returns all environment variables, helpful for debugging MCP server configuration

## Arguments
- This tool does not expose structured input arguments.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Semantic hints
No explicit semantic hints for this condition.

## Examples
No synthesized examples for this condition.
