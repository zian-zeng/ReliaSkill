# move_file

**Condition:** `retrieved_docs`

## Summary
Move or rename files and directories. Can move files between directories and rename them in a single operation. If the destination exists, the operation will fail. Works across different directories and can be used for simple renaming within the same directory. Both source and destination must be within allowed directories. Move File

## When to use
- Move or rename files and directories. Can move files between directories and rename them in a single operation. If the destination exists, the operation will fail. Works across different directories and can be used for simple renaming within the same directory. Both source and destination must be within allowed directories.
- Move File
- destination required
- source required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for move_file
```json
{
  "source": "sample_source_1",
  "destination": "sample_destination_1"
}
```
- Retrieved-docs fuller call for move_file
```json
{
  "source": "sample_source_2",
  "destination": "sample_destination_2"
}
```
