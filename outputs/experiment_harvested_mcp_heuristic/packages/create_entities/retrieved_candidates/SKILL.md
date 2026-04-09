# create_entities

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `create_entities` over nearby tools using cues like create_entities.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `create_entities` when the request matches its role.
- Shortlist: create_entities, create_relations, add_observations.
- Create multiple new entities in the knowledge graph
- Create multiple new entities in the knowledge graph

## When not to use
- Do not confuse `create_entities` with `create_relations`: Create multiple new relations between entities in the knowledge graph. Relations should be in active voice
- Do not confuse `create_entities` with `add_observations`: Add new observations to existing entities in the knowledge graph

## Arguments
- `entities`, array, required: No description provided.

## Argument template
```json
{
  "entities": [
    {}
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for create_entities
```json
{
  "entities": [
    {}
  ]
}
```
