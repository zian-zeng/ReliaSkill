# git_create_branch

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `git_create_branch` over nearby tools using cues like git_create_branch, creates, branch, from.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `git_create_branch` when the request matches its role.
- Shortlist: git_create_branch, write_file, create_directory.
- Creates a new branch from an optional base branch
- Creates a new branch from an optional base branch

## When not to use
- Do not confuse `git_create_branch` with `write_file`: Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories.
- Do not confuse `git_create_branch` with `create_directory`: Create a new directory or ensure a directory exists. Can create multiple nested directories in one operation. If the directory already exists, this operation will succeed silently. Perfect for setting up directory structures for projects or ensuring required paths exist. Only works within allowed directories.

## Arguments
- `repo_path`, string, required: No description provided.
- `branch_name`, string, required: No description provided.
- `base_branch`, string, optional: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name",
  "base_branch": "sample_base_branch_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for git_create_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name"
}
```
- Full routed call for git_create_branch
```json
{
  "repo_path": "data/sample.txt",
  "branch_name": "sample-name",
  "base_branch": "sample_base_branch_2"
}
```
