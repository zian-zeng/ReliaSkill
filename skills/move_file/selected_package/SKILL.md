# move_file

**Condition:** `multi_candidate_skill`

## Summary
Move or rename files and directories. Can move files between directories and rename them in a single operation. If the destination exists, the operation will fail. Works across different directories and can be used for simple renaming within the same.

## When to use
- Use `move_file` when the user's request directly matches this tool's purpose.
- Provide all required fields: `source`, and `destination`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `source`, string, required: No description provided.
- `destination`, string, required: No description provided.

## Argument template
```json
{
  "source": "sample_source_1",
  "destination": "sample_destination_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for move_file
```json
{
  "source": "sample_source_1",
  "destination": "sample_destination_1"
}
```
- Richer invocation that uses optional controls for move_file
```json
{
  "source": "sample_source_2",
  "destination": "sample_destination_2"
}
```
