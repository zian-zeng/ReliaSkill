# trigger-sampling-request

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `trigger-sampling-request` over nearby tools using cues like trigger-sampling-request.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `trigger-sampling-request` when the request matches its role.
- Shortlist: trigger-sampling-request, trigger-sampling-request-async, trigger-elicitation-request.
- Trigger a Request from the Server for LLM Sampling
- Trigger a Request from the Server for LLM Sampling

## When not to use
- Do not confuse `trigger-sampling-request` with `trigger-sampling-request-async`: Trigger an async sampling request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends a request and the client executes it asynchronously, allowing the server to poll for progress and results.
- Do not confuse `trigger-sampling-request` with `trigger-elicitation-request`: Trigger a Request from the Server for User Elicitation

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
- Minimal routed call for trigger-sampling-request
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_1"
}
```
- Full routed call for trigger-sampling-request
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_2"
}
```
