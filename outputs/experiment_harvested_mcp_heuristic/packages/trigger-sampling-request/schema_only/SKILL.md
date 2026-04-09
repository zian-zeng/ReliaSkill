# trigger-sampling-request

**Condition:** `schema_only`

## Summary
Trigger a Request from the Server for LLM Sampling

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for trigger-sampling-request
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_1"
}
```
- Schema-aligned full call for trigger-sampling-request
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_2"
}
```
