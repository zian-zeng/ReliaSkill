# delete_entities

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `delete_entities` over nearby tools using cues like delete_entities, their, associated, entitynames.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `delete_entities` when the request matches its role.
- Shortlist: delete_entities, delete_relations, delete_observations.
- Delete multiple entities and their associated relations from the knowledge graph
- Delete multiple entities and their associated relations from the knowledge graph

## When not to use
- Do not confuse `delete_entities` with `delete_relations`: Delete multiple relations from the knowledge graph
- Do not confuse `delete_entities` with `delete_observations`: Delete specific observations from entities in the knowledge graph

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
- Minimal routed call for delete_entities
```json
{
  "entityNames": [
    "sample-name"
  ]
}
```
