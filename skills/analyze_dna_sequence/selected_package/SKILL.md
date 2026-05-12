# analyze_dna_sequence

**Condition:** `multi_candidate_skill`

## Summary
Analyzes the DNA sequence based on a reference sequence and return any potential mutations. Provide all required fields: `sequence`, and `reference_sequence`.

## When to use
- Use `analyze_dna_sequence` when the user's request directly matches this tool's purpose.
- Provide all required fields: `sequence`, and `reference_sequence`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `mutation_type`: 'insertion', 'deletion', 'substitution'.
- Do not use when required inputs are missing.

## Arguments
- `sequence`, string, required: The DNA sequence to be analyzed.
- `reference_sequence`, string, required: The reference DNA sequence.
- `mutation_type`, string, optional, enum=['insertion', 'deletion', 'substitution']: Type of the mutation to be looked for in the sequence. Default to 'substitution'.

## Argument template
```json
{
  "sequence": "sample_sequence_1",
  "reference_sequence": "sample_reference_sequence_1",
  "mutation_type": "insertion"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for analyze_dna_sequence
```json
{
  "sequence": "sample_sequence_1",
  "reference_sequence": "sample_reference_sequence_1"
}
```
- Richer invocation that uses optional controls for analyze_dna_sequence
```json
{
  "sequence": "sample_sequence_2",
  "reference_sequence": "sample_reference_sequence_2",
  "mutation_type": "deletion"
}
```
