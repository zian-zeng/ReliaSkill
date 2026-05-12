# delete_entities

**Condition:** `multi_candidate_skill`

## Summary
Delete multiple entities and their associated relations from the knowledge graph. Provide the required field `entityNames`.

## When to use
- Use `delete_entities` when the user's request directly matches this tool's purpose.
- Provide the required field `entityNames`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

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
- Required-argument dev behavior example.
```json
{
  "entityNames": [
    "sample-name"
  ]
}
```
