# calculate_density

**Condition:** `multi_candidate_skill`

## Summary
Calculate the population density of a specific country in a specific year. Provide all required fields: `country`, `year`, `population`, and `land_area`.

## When to use
- Use `calculate_density` when the user's request directly matches this tool's purpose.
- Provide all required fields: `country`, `year`, `population`, and `land_area`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `country`, string, required: The country for which the density needs to be calculated.
- `year`, string, required: The year in which the density is to be calculated.
- `population`, integer, required: The population of the country.
- `land_area`, float, required: The land area of the country in square kilometers.

## Argument template
```json
{
  "country": "sample_country_1",
  "year": "sample_year_1",
  "population": 1,
  "land_area": null
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_density
```json
{
  "country": "sample_country_1",
  "year": "sample_year_1",
  "population": 1,
  "land_area": null
}
```
- Richer invocation that uses optional controls for calculate_density
```json
{
  "country": "sample_country_2",
  "year": "sample_year_2",
  "population": 2,
  "land_area": null
}
```
