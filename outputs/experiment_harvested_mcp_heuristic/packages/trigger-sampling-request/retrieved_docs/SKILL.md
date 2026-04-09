# trigger-sampling-request

**Condition:** `retrieved_docs`

## Summary
Trigger a Request from the Server for LLM Sampling Trigger Sampling Request Tool

## When to use
- Trigger a Request from the Server for LLM Sampling
- Trigger Sampling Request Tool
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
- Retrieved-docs minimal call for trigger-sampling-request
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_1"
}
```
- Retrieved-docs fuller call for trigger-sampling-request
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_2"
}
```
