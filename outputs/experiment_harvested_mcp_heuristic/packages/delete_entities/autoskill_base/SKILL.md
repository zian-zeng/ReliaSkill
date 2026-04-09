# delete_entities

**Condition:** `autoskill_base`

## Summary
Delete multiple entities and their associated relations from the knowledge graph. Provide the required field `entityNames`.

## When to use
- Use `delete_entities` when the user's request directly matches this tool's purpose.
- Provide the required field `entityNames`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

## Arguments
- `entityNames`, array, required: No description provided.

## Argument template
```json
{
  "entityNames": [
    "sample-name"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for delete_entities
```json
{
  "entityNames": [
    "sample-name"
  ]
}
```
- Richer invocation that uses optional controls for delete_entities
```json
{
  "entityNames": [
    "sample-name"
  ]
}
```
