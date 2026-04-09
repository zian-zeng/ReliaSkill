# delete_relations

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `delete_relations` over nearby tools using cues like delete_relations.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `delete_relations` when the request matches its role.
- Shortlist: delete_relations, delete_entities, delete_observations.
- Delete multiple relations from the knowledge graph
- Delete multiple relations from the knowledge graph

## When not to use
- Do not confuse `delete_relations` with `delete_entities`: Delete multiple entities and their associated relations from the knowledge graph
- Do not confuse `delete_relations` with `delete_observations`: Delete specific observations from entities in the knowledge graph

## Arguments
- `relations`, array, required: No description provided.

## Argument template
```json
{
  "relations": [
    {}
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for delete_relations
```json
{
  "relations": [
    {}
  ]
}
```
