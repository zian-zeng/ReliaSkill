# trigger-sampling-request

**Condition:** `multi_candidate_skill`

## Summary
Trigger a Request from the Server for LLM Sampling. Provide the required field `prompt`.

## When to use
- Use `trigger-sampling-request` when the user's request directly matches this tool's purpose.
- Provide the required field `prompt`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `prompt`, string, required: No description provided.
- `maxTokens`, string, optional: No description provided.

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
  "prompt": "Summarize the latest update."
}
```
- Richer invocation that uses optional controls for trigger-sampling-request
```json
{
  "prompt": "Summarize the latest update.",
  "maxTokens": "sample_maxTokens_2"
}
```
