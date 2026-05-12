# get_codegen_session

**Condition:** `multi_candidate_skill`

## Summary
Get information about a code generation session. Provide the required field `sessionId`.

## When to use
- Use `get_codegen_session` when the user's request directly matches this tool's purpose.
- Provide the required field `sessionId`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `sessionId`, string, required: ID of the session to retrieve

## Argument template
```json
{
  "sessionId": "sample_sessionId_4"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for get_codegen_session
```json
{
  "sessionId": "sample_sessionId_1"
}
```
- Richer invocation that uses optional controls for get_codegen_session
```json
{
  "sessionId": "sample_sessionId_2"
}
```
- Required-argument dev behavior example.
```json
{
  "sessionId": "sample_sessionId_3"
}
```
- Optional, enum, nested, or array argument example.
```json
{
  "sessionId": "sample_sessionId_4"
}
```
