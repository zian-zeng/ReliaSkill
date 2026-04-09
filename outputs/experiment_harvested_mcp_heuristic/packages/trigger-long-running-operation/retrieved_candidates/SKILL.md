# trigger-long-running-operation

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `trigger-long-running-operation` over nearby tools using cues like trigger-long-running-operation, long, running, operation.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `trigger-long-running-operation` when the request matches its role.
- Shortlist: trigger-long-running-operation, trigger-sampling-request-async, trigger-elicitation-request-async.
- Demonstrates a long running operation with progress updates.
- Demonstrates a long running operation with progress updates.

## When not to use
- Do not confuse `trigger-long-running-operation` with `trigger-sampling-request-async`: Trigger an async sampling request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends a request and the client executes it asynchronously, allowing the server to poll for progress and results.
- Do not confuse `trigger-long-running-operation` with `trigger-elicitation-request-async`: Trigger an async elicitation request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends an elicitation request and the client handles user input asynchronously, allowing the server to poll for completion.

## Arguments
- `duration`, string, required: No description provided.
- `steps`, number, required: No description provided.

## Argument template
```json
{
  "duration": "sample_duration_1",
  "steps": 1.0
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for trigger-long-running-operation
```json
{
  "duration": "sample_duration_1",
  "steps": 1.0
}
```
- Full routed call for trigger-long-running-operation
```json
{
  "duration": "sample_duration_2",
  "steps": 2.0
}
```
