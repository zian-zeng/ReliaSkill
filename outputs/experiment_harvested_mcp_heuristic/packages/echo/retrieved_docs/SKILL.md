# echo

**Condition:** `retrieved_docs`

## Summary
Echoes back the input string Echo Tool

## When to use
- Echoes back the input string
- Echo Tool
- message required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for echo
```json
{
  "message": "sample_message_1"
}
```
- Retrieved-docs fuller call for echo
```json
{
  "message": "sample_message_2"
}
```
