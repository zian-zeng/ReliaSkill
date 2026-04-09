# delete_entities

**Condition:** `retrieved_docs`

## Summary
Delete multiple entities and their associated relations from the knowledge graph Delete Entities

## When to use
- Delete multiple entities and their associated relations from the knowledge graph
- Delete Entities
- entityNames required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for delete_entities
```json
{
  "entityNames": [
    "sample-name"
  ]
}
```
