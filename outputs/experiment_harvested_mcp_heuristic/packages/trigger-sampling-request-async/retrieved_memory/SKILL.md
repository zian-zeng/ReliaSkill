# trigger-sampling-request-async

**Condition:** `retrieved_memory`

## Summary
Trigger an async sampling request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends a request and the client executes it asynchronously, allowing the server to poll for progress and results.

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

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
- Minimal valid memory-backed call for trigger-sampling-request-async
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_1"
}
```
