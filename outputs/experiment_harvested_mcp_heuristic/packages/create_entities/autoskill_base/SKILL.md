# create_entities

**Condition:** `autoskill_base`

## Summary
Create multiple new entities in the knowledge graph. Provide the required field `entities`.

## When to use
- Use `create_entities` when the user's request directly matches this tool's purpose.
- Provide the required field `entities`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
