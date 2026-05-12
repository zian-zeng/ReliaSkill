# add_observations

**Condition:** `multi_candidate_skill`

## Summary
Add new observations to existing entities in the knowledge graph. Provide the required field `observations`.

## When to use
- Use `add_observations` when the user's request directly matches this tool's purpose.
- Provide the required field `observations`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

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
- Minimal valid request that satisfies the required fields for add_observations
```json
{
  "observations": [
    {}
  ]
}
```
- Richer invocation that uses optional controls for add_observations
```json
{
  "observations": [
    {}
  ]
}
```
- Required-argument dev behavior example.
```json
{
  "observations": [
    {}
  ]
}
```
