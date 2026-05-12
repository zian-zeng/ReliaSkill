# calculate_genotype_frequency

**Condition:** `multi_candidate_skill`

## Summary
Calculate the frequency of homozygous dominant genotype based on the allele frequency using Hardy Weinberg Principle. Provide all required fields: `allele_frequency`, and `genotype`.

## When to use
- Use `calculate_genotype_frequency` when the user's request directly matches this tool's purpose.
- Provide all required fields: `allele_frequency`, and `genotype`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `genotype`: 'AA', 'Aa', 'aa'.
- Do not use when required inputs are missing.

## Arguments
- `allele_frequency`, float, required: The frequency of the dominant allele in the population.
- `genotype`, string, required, enum=['AA', 'Aa', 'aa']: The genotype which frequency is needed, default is homozygous dominant.

## Argument template
```json
{
  "allele_frequency": null,
  "genotype": "AA"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_genotype_frequency
```json
{
  "allele_frequency": null,
  "genotype": "AA"
}
```
- Richer invocation that uses optional controls for calculate_genotype_frequency
```json
{
  "allele_frequency": null,
  "genotype": "Aa"
}
```
