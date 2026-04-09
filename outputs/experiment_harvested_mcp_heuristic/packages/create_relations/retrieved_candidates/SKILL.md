# create_relations

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `create_relations` over nearby tools using cues like create_relations, relations, between, graph..

## When to use
- Retrieve a shortlist of nearby tools first, then choose `create_relations` when the request matches its role.
- Shortlist: create_relations, create_entities, add_observations.
- Create multiple new relations between entities in the knowledge graph. Relations should be in active voice
- Create multiple new relations between entities in the knowledge graph. Relations should be in active voice

## When not to use
- Do not confuse `create_relations` with `create_entities`: Create multiple new entities in the knowledge graph
- Do not confuse `create_relations` with `add_observations`: Add new observations to existing entities in the knowledge graph

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
- Minimal routed call for create_relations
```json
{
  "relations": [
    {}
  ]
}
```
