# create_directory

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `create_directory` over nearby tools using cues like create_directory, create, ensure, exists..

## When to use
- Retrieve a shortlist of nearby tools first, then choose `create_directory` when the request matches its role.
- Shortlist: create_directory, list_directory, search_files.
- Create a new directory or ensure a directory exists. Can create multiple nested directories in one operation. If the directory already exists, this operation will succeed silently. Perfect for setting up directory structures for projects or ensuring required paths exist. Only works within allowed directories.
- Create a new directory or ensure a directory exists. Can create multiple nested directories in one operation. If the directory already exists, this operation will succeed silently. Perfect for setting up directory structures for projects or ensuring required paths exist. Only works within allowed directories.

## When not to use
- Do not confuse `create_directory` with `list_directory`: Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory. Only works within allowed directories.
- Do not confuse `create_directory` with `search_files`: Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you do not know their exact location. Only searches within allowed directories.

## Arguments
- `path`, string, required: Directory path to create within an allowed directory.

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
