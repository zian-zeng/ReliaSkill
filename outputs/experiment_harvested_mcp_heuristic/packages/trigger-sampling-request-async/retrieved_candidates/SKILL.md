# trigger-sampling-request-async

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `trigger-sampling-request-async` over nearby tools using cues like trigger-sampling-request-async, progress, results..

## When to use
- Retrieve a shortlist of nearby tools first, then choose `trigger-sampling-request-async` when the request matches its role.
- Shortlist: trigger-sampling-request-async, trigger-elicitation-request-async, trigger-sampling-request.
- Trigger an async sampling request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends a request and the client executes it asynchronously, allowing the server to poll for progress and results.
- Trigger an async sampling request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends a request and the client executes it asynchronously, allowing the server to poll for progress and results.

## When not to use
- Do not confuse `trigger-sampling-request-async` with `trigger-elicitation-request-async`: Trigger an async elicitation request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends an elicitation request and the client handles user input asynchronously, allowing the server to poll for completion.
- Do not confuse `trigger-sampling-request-async` with `trigger-sampling-request`: Trigger a Request from the Server for LLM Sampling

## Arguments
- `prompt`, string, required: No description provided.
- `maxTokens`, string, required: No description provided.

## Argument template
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for trigger-sampling-request-async
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_1"
}
```
- Full routed call for trigger-sampling-request-async
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_2"
}
```
