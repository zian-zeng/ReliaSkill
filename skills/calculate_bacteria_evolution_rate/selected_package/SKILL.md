# calculate_bacteria_evolution_rate

**Condition:** `multi_candidate_skill`

## Summary
Calculate the evolution rate of bacteria given the starting number, duplication frequency and total duration. Provide all required fields: `start_population`, `duplication_frequency`, and `duration`.

## When to use
- Use `calculate_bacteria_evolution_rate` when the user's request directly matches this tool's purpose.
- Provide all required fields: `start_population`, `duplication_frequency`, and `duration`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `start_population`, integer, required: The starting population of bacteria.
- `duplication_frequency`, integer, required: The frequency of bacteria duplication per hour.
- `duration`, integer, required: Total duration in hours.
- `generation_time`, integer, optional: The average generation time of the bacteria in minutes. Default is 20 minutes

## Argument template
```json
{
  "start_population": 1,
  "duplication_frequency": 1,
  "duration": 1,
  "generation_time": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_bacteria_evolution_rate
```json
{
  "start_population": 1,
  "duplication_frequency": 1,
  "duration": 1
}
```
- Richer invocation that uses optional controls for calculate_bacteria_evolution_rate
```json
{
  "start_population": 2,
  "duplication_frequency": 2,
  "duration": 2,
  "generation_time": 2
}
```
