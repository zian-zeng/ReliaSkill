# echo

**Condition:** `multi_candidate_skill`

## Summary
Echoes back the input string. Provide the required field `message`.

## When to use
- Use `echo` when the user's request directly matches this tool's purpose.
- Provide the required field `message`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `message`, string, required: No description provided.

## Argument template
```json
{
  "message": "sample_message_4"
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
- Required-argument dev behavior example.
```json
{
  "message": "sample_message_3"
}
```
- Optional, enum, nested, or array argument example.
```json
{
  "message": "sample_message_4"
}
```
