# echo

**Condition:** `autoskill_base`

## Summary
Echoes back the input string. Provide the required field `message`.

## When to use
- Use `echo` when the user's request directly matches this tool's purpose.
- Provide the required field `message`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

## Arguments
- `message`, string, required: No description provided.

## Argument template
```json
{
  "message": "sample_message_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for echo
```json
{
  "message": "sample_message_1"
}
```
- Richer invocation that uses optional controls for echo
```json
{
  "message": "sample_message_2"
}
```
