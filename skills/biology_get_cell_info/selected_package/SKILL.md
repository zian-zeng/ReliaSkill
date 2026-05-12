# biology.get_cell_info

**Condition:** `multi_candidate_skill`

## Summary
Retrieve information about the structure and functioning of a specified type of cell. Provide the required field `cell_type`.

## When to use
- Use `biology.get_cell_info` when the user's request directly matches this tool's purpose.
- Provide the required field `cell_type`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `cell_type`, string, required: Type of cell you want information about
- `detailed`, boolean, optional, default='false': Indicate if you want a detailed description of the cell

## Argument template
```json
{
  "cell_type": "sample_cell_type_1",
  "detailed": "false"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for biology.get_cell_info
```json
{
  "cell_type": "sample_cell_type_1"
}
```
- Richer invocation that uses optional controls for biology.get_cell_info
```json
{
  "cell_type": "sample_cell_type_2",
  "detailed": "false"
}
```
