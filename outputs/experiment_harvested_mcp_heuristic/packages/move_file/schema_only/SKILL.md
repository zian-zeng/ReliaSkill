# move_file

**Condition:** `schema_only`

## Summary
Move or rename files and directories. Can move files between directories and rename them in a single operation. If the destination exists, the operation will fail. Works across different directories and can be used for simple renaming within the same directory. Both source and destination must be within allowed directories.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for move_file
```json
{
  "source": "sample_source_1",
  "destination": "sample_destination_1"
}
```
- Schema-aligned full call for move_file
```json
{
  "source": "sample_source_2",
  "destination": "sample_destination_2"
}
```
