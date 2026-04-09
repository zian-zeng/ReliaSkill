# git_diff_unstaged

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `git_diff_unstaged` over nearby tools using cues like git_diff_unstaged.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `git_diff_unstaged` when the request matches its role.
- Shortlist: git_diff_unstaged, git_diff_staged, search_files.
- Shows changes in the working directory that are not yet staged
- Shows changes in the working directory that are not yet staged

## When not to use
- Do not confuse `git_diff_unstaged` with `git_diff_staged`: Shows changes that are staged for commit
- Do not confuse `git_diff_unstaged` with `search_files`: Recursively search for files and directories matching a pattern. The patterns should be glob-style patterns that match paths relative to the working directory. Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. Returns full paths to all matching items. Great for finding files when you don't know their exact location. Only searches within allowed directories.

## Arguments
- `repo_path`, string, required: No description provided.
- `context_lines`, integer, optional: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "context_lines": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for git_diff_unstaged
```json
{
  "repo_path": "data/sample.txt"
}
```
- Full routed call for git_diff_unstaged
```json
{
  "repo_path": "data/sample.txt",
  "context_lines": 2
}
```
