# create_entities

**Condition:** `multi_candidate_skill`

## Summary
Create multiple new entities in the knowledge graph. Provide the required field `entities`.

## When to use
- Use `create_entities` when the user's request directly matches this tool's purpose.
- Provide the required field `entities`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

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
- Minimal valid request that satisfies the required fields for create_entities
```json
{
  "entities": [
    {}
  ]
}
```
- Richer invocation that uses optional controls for create_entities
```json
{
  "entities": [
    {}
  ]
}
```
- Required-argument dev behavior example.
```json
{
  "entities": [
    {}
  ]
}
```
