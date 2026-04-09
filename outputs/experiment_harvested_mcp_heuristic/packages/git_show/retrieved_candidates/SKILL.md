# git_show

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `git_show` over nearby tools using cues like git_show, revision.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `git_show` when the request matches its role.
- Shortlist: git_show, git_log, read_file.
- Shows the contents of a commit
- Shows the contents of a commit

## When not to use
- Do not confuse `git_show` with `git_log`: Shows the commit logs
- Do not confuse `git_show` with `read_file`: Read the complete contents of a file as text. DEPRECATED: Use read_text_file instead.

## Arguments
- `repo_path`, string, required: No description provided.
- `revision`, string, required: No description provided.

## Argument template
```json
{
  "repo_path": "data/sample.txt",
  "revision": "sample_revision_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for git_show
```json
{
  "repo_path": "data/sample.txt",
  "revision": "sample_revision_1"
}
```
- Full routed call for git_show
```json
{
  "repo_path": "data/sample.txt",
  "revision": "sample_revision_2"
}
```
