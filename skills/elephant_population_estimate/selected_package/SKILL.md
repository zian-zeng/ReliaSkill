# elephant_population_estimate

**Condition:** `multi_candidate_skill`

## Summary
Estimate future population of elephants given current population and growth rate. Provide all required fields: `current_population`, `growth_rate`, and `years`.

## When to use
- Use `elephant_population_estimate` when the user's request directly matches this tool's purpose.
- Provide all required fields: `current_population`, `growth_rate`, and `years`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `current_population`, integer, required: The current number of elephants.
- `growth_rate`, float, required: The annual population growth rate of elephants.
- `years`, integer, required: The number of years to project the population.

## Argument template
```json
{
  "current_population": 1,
  "growth_rate": null,
  "years": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for elephant_population_estimate
```json
{
  "current_population": 1,
  "growth_rate": null,
  "years": 1
}
```
- Richer invocation that uses optional controls for elephant_population_estimate
```json
{
  "current_population": 2,
  "growth_rate": null,
  "years": 2
}
```
