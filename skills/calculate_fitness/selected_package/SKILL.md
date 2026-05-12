# calculate_fitness

**Condition:** `multi_candidate_skill`

## Summary
Calculate the expected evolutionary fitness of a creature based on the individual values and contributions of its traits. Provide all required fields: `trait_values`, and `trait_contributions`.

## When to use
- Use `calculate_fitness` when the user's request directly matches this tool's purpose.
- Provide all required fields: `trait_values`, and `trait_contributions`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `trait_values`, array, required: List of trait values, which are decimal numbers between 0 and 1, where 1 represents the trait maximally contributing to fitness.
- `trait_contributions`, array, required: List of the percentage contributions of each trait to the overall fitness, which must sum to 1.

## Argument template
```json
{
  "trait_values": [
    null
  ],
  "trait_contributions": [
    null
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_fitness
```json
{
  "trait_values": [
    null
  ],
  "trait_contributions": [
    null
  ]
}
```
- Richer invocation that uses optional controls for calculate_fitness
```json
{
  "trait_values": [
    null
  ],
  "trait_contributions": [
    null
  ]
}
```
- Required-argument dev behavior example.
```json
{
  "trait_values": [
    null
  ],
  "trait_contributions": [
    null
  ]
}
```
