# cell_biology.function_lookup

**Condition:** `multi_candidate_skill`

## Summary
Look up the function of a given molecule in a specified organelle. Provide all required fields: `molecule`, `organelle`, and `specific_function`.

## When to use
- Use `cell_biology.function_lookup` when the user's request directly matches this tool's purpose.
- Provide all required fields: `molecule`, `organelle`, and `specific_function`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `molecule`, string, required: The molecule of interest.
- `organelle`, string, required: The organelle of interest.
- `specific_function`, boolean, required: If set to true, a specific function of the molecule within the organelle will be provided, if such information exists.

## Argument template
```json
{
  "molecule": "sample_molecule_1",
  "organelle": "sample_organelle_1",
  "specific_function": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for cell_biology.function_lookup
```json
{
  "molecule": "sample_molecule_1",
  "organelle": "sample_organelle_1",
  "specific_function": false
}
```
- Richer invocation that uses optional controls for cell_biology.function_lookup
```json
{
  "molecule": "sample_molecule_2",
  "organelle": "sample_organelle_2",
  "specific_function": true
}
```
