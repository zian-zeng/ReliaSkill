# move_file

**Condition:** `autoskill_base`

## Summary
Move or rename files and directories. Can move files between directories and rename them in a single operation. If the destination exists, the operation will fail. Works across different directories and can be used for simple renaming within the same directory. Both source and destination must be within allowed directories. Provide all required fields: `source`, and `destination`.

## When to use
- Use `move_file` when the user's request directly matches this tool's purpose.
- Provide all required fields: `source`, and `destination`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
