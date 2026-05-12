# cellbio.get_proteins

**Condition:** `multi_candidate_skill`

## Summary
Get the list of proteins in a specific cell compartment. Provide the required field `cell_compartment`.

## When to use
- Use `cellbio.get_proteins` when the user's request directly matches this tool's purpose.
- Provide the required field `cell_compartment`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `cell_compartment`, string, required: The specific cell compartment.
- `include_description`, boolean, optional, default='false': Set true if you want a brief description of each protein.

## Argument template
```json
{
  "cell_compartment": "sample_cell_compartment_1",
  "include_description": "false"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for cellbio.get_proteins
```json
{
  "cell_compartment": "sample_cell_compartment_1"
}
```
- Richer invocation that uses optional controls for cellbio.get_proteins
```json
{
  "cell_compartment": "sample_cell_compartment_2",
  "include_description": "false"
}
```
