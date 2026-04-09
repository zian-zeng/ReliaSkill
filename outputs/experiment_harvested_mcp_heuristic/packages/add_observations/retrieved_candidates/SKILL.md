# add_observations

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `add_observations` over nearby tools using cues like add_observations, existing.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `add_observations` when the request matches its role.
- Shortlist: add_observations, create_entities, delete_observations.
- Add new observations to existing entities in the knowledge graph
- Add new observations to existing entities in the knowledge graph

## When not to use
- Do not confuse `add_observations` with `create_entities`: Create multiple new entities in the knowledge graph
- Do not confuse `add_observations` with `delete_observations`: Delete specific observations from entities in the knowledge graph

## Arguments
- `observations`, array, required: No description provided.

## Argument template
```json
{
  "observations": [
    {}
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for add_observations
```json
{
  "observations": [
    {}
  ]
}
```
