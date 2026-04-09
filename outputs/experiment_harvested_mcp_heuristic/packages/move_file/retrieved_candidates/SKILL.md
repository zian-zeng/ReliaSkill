# move_file

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `move_file` over nearby tools using cues like move_file, move, rename, them.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `move_file` when the request matches its role.
- Shortlist: move_file, create_directory, list_directory.
- Move or rename files and directories. Can move files between directories and rename them in a single operation. If the destination exists, the operation will fail. Works across different directories and can be used for simple renaming within the same directory. Both source and destination must be within allowed directories.
- Move or rename files and directories. Can move files between directories and rename them in a single operation. If the destination exists, the operation will fail. Works across different directories and can be used for simple renaming within the same directory. Both source and destination must be within allowed directories.

## When not to use
- Do not confuse `move_file` with `create_directory`: Create a new directory or ensure a directory exists. Can create multiple nested directories in one operation. If the directory already exists, this operation will succeed silently. Perfect for setting up directory structures for projects or ensuring required paths exist. Only works within allowed directories.
- Do not confuse `move_file` with `list_directory`: Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory. Only works within allowed directories.

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
- Minimal routed call for move_file
```json
{
  "source": "sample_source_1",
  "destination": "sample_destination_1"
}
```
- Full routed call for move_file
```json
{
  "source": "sample_source_2",
  "destination": "sample_destination_2"
}
```
