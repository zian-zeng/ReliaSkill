# git_commit

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `git_commit` over nearby tools using cues like git_commit, records, repository, message.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `git_commit` when the request matches its role.
- Shortlist: git_commit, edit_file, git_add.
- Records changes to the repository
- Records changes to the repository

## When not to use
- Do not confuse `git_commit` with `edit_file`: Make line-based edits to a text file. Each edit replaces exact line sequences with new content. Returns a git-style diff showing the changes made. Only works within allowed directories.
- Do not confuse `git_commit` with `git_add`: Adds file contents to the staging area

## Arguments
- `repo_path`, string, required: No description provided.
- `message`, string, required: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "message": "sample_message_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for git_commit
```json
{
  "repo_path": "data/sample.txt",
  "message": "sample_message_1"
}
```
- Full routed call for git_commit
```json
{
  "repo_path": "data/sample.txt",
  "message": "sample_message_2"
}
```
