# search_nodes

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `search_nodes` over nearby tools using cues like search_nodes, based, query.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `search_nodes` when the request matches its role.
- Shortlist: search_nodes, open_nodes, search_files.
- Search for nodes in the knowledge graph based on a query
- Search for nodes in the knowledge graph based on a query

## When not to use
- Do not confuse `search_nodes` with `open_nodes`: Open specific nodes in the knowledge graph by their names
- Do not confuse `search_nodes` with `search_files`: Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you don't know their exact location. Only searches within allowed directories.

## Arguments
- `query`, string, required: No description provided.

## Argument template
```json
{
  "query": "sample query"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for search_nodes
```json
{
  "query": "sample query"
}
```
