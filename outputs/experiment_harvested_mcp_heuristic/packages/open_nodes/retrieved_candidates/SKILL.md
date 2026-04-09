# open_nodes

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `open_nodes` over nearby tools using cues like open_nodes, open, their, names.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `open_nodes` when the request matches its role.
- Shortlist: open_nodes, delete_observations, search_nodes.
- Open specific nodes in the knowledge graph by their names
- Open specific nodes in the knowledge graph by their names

## When not to use
- Do not confuse `open_nodes` with `delete_observations`: Delete specific observations from entities in the knowledge graph
- Do not confuse `open_nodes` with `search_nodes`: Search for nodes in the knowledge graph based on a query

## Arguments
- `names`, array, required: No description provided.

## Argument template
```json
{
  "names": [
    "sample-name"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for open_nodes
```json
{
  "names": [
    "sample-name"
  ]
}
```
