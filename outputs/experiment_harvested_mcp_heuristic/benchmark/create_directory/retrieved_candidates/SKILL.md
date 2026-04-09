# create_directory

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `create_directory` over nearby tools using cues like create_directory, create, directory, ensure.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `create_directory` when the request matches its role.
- Shortlist: create_directory, move_file, read_multiple_files.
- Create a new directory or ensure a directory exists. Can create multiple nested directories in one operation. If the directory already exists, this operation will succeed silently. Perfect for setting up directory structures for projects or ensuring required paths exist. Only works within allowed directories.
- Create a new directory or ensure a directory exists. Can create multiple nested directories in one operation. If the directory already exists, this operation will succeed silently. Perfect for setting up directory structures for projects or ensuring required paths exist. Only works within allowed directories.

## When not to use
- Do not confuse `create_directory` with `move_file`: Move or rename files and directories. Can move files between directories and rename them in a single operation. If the destination exists, the operation will fail. Works across different directories and can be used for simple renaming within the same directory. Both source and destination must be within allowed directories.
- Do not confuse `create_directory` with `read_multiple_files`: Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories.

## Arguments
- `path`, string, required: No description provided.

## Argument template
```json
{
  "path": "data/sample.txt"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for create_directory
```json
{
  "path": "data/sample.txt"
}
```
- Route ensure-directory requests here.
```json
{
  "path": "reports/weekly"
}
```
