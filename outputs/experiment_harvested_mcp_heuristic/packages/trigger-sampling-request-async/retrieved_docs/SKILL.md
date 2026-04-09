# trigger-sampling-request-async

**Condition:** `retrieved_docs`

## Summary
Trigger an async sampling request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends a request and the client executes it asynchronously, allowing the server to poll for progress and results. Trigger Async Sampling Request Tool

## When to use
- Trigger an async sampling request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends a request and the client executes it asynchronously, allowing the server to poll for progress and results.
- Trigger Async Sampling Request Tool
- maxTokens required
- prompt required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for trigger-sampling-request-async
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_1"
}
```
- Retrieved-docs fuller call for trigger-sampling-request-async
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_2"
}
```
