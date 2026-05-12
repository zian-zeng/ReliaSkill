# create_relations

**Condition:** `multi_candidate_skill`

## Summary
Create multiple new relations between entities in the knowledge graph. Relations should be in active voice. Provide the required field `relations`.

## When to use
- Use `create_relations` when the user's request directly matches this tool's purpose.
- Provide the required field `relations`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

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
- Minimal valid request that satisfies the required fields for create_relations
```json
{
  "relations": [
    {}
  ]
}
```
- Richer invocation that uses optional controls for create_relations
```json
{
  "relations": [
    {}
  ]
}
```
- Required-argument dev behavior example.
```json
{
  "relations": [
    {}
  ]
}
```
