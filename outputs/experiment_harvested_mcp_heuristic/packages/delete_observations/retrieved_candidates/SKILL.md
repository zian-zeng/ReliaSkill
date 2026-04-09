# delete_observations

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `delete_observations` over nearby tools using cues like delete_observations, specific, deletions.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `delete_observations` when the request matches its role.
- Shortlist: delete_observations, add_observations, delete_entities.
- Delete specific observations from entities in the knowledge graph
- Delete specific observations from entities in the knowledge graph

## When not to use
- Do not confuse `delete_observations` with `add_observations`: Add new observations to existing entities in the knowledge graph
- Do not confuse `delete_observations` with `delete_entities`: Delete multiple entities and their associated relations from the knowledge graph

## Arguments
- `deletions`, array, required: No description provided.

## Argument template
```json
{
  "deletions": [
    {}
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for delete_observations
```json
{
  "deletions": [
    {}
  ]
}
```
