# trigger-elicitation-request

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `trigger-elicitation-request` over nearby tools using cues like trigger-elicitation-request, from.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `trigger-elicitation-request` when the request matches its role.
- Shortlist: trigger-elicitation-request, trigger-elicitation-request-async, get-env.
- Trigger a Request from the Server for User Elicitation
- Trigger a Request from the Server for User Elicitation

## When not to use
- Do not confuse `trigger-elicitation-request` with `trigger-elicitation-request-async`: Trigger an async elicitation request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends an elicitation request and the client handles user input asynchronously, allowing the server to poll for completion.
- Do not confuse `trigger-elicitation-request` with `get-env`: Returns all environment variables, helpful for debugging MCP server configuration

## Arguments
- This tool does not expose structured input arguments.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Semantic hints
No explicit semantic hints for this condition.

## Examples
No synthesized examples for this condition.
