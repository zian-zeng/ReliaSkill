# open_nodes

**Condition:** `multi_candidate_skill`

## Summary
Open specific nodes in the knowledge graph by their names. Provide the required field `names`.

## When to use
- Use `open_nodes` when the user's request directly matches this tool's purpose.
- Provide the required field `names`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

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
- Required-argument dev behavior example.
```json
{
  "names": [
    "sample-name"
  ]
}
```
