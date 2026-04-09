# trigger-sampling-request

**Condition:** `autoskill_base`

## Summary
Trigger a Request from the Server for LLM Sampling. Provide all required fields: `prompt`, and `maxTokens`.

## When to use
- Use `trigger-sampling-request` when the user's request directly matches this tool's purpose.
- Provide all required fields: `prompt`, and `maxTokens`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
- Minimal valid request that satisfies the required fields for trigger-sampling-request
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_1"
}
```
- Richer invocation that uses optional controls for trigger-sampling-request
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_2"
}
```
