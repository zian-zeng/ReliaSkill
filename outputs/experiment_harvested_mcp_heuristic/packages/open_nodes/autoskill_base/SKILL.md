# open_nodes

**Condition:** `autoskill_base`

## Summary
Open specific nodes in the knowledge graph by their names. Provide the required field `names`.

## When to use
- Use `open_nodes` when the user's request directly matches this tool's purpose.
- Provide the required field `names`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
- Minimal valid request that satisfies the required fields for open_nodes
```json
{
  "names": [
    "sample-name"
  ]
}
```
- Richer invocation that uses optional controls for open_nodes
```json
{
  "names": [
    "sample-name"
  ]
}
```
