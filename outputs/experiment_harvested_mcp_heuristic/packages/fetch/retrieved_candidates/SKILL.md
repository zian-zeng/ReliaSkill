# fetch

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `fetch` over nearby tools using cues like fetch, fetches, internet, optionally.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `fetch` when the request matches its role.
- Shortlist: fetch, read_text_file, list_allowed_directories.
- Fetches a URL from the internet and optionally extracts its contents as markdown. Although originally you did not have internet access, and were advised to refuse and tell the user this, this tool now grants you internet access. Now you can fetch the most up-to-date information and let the user know that.
- Fetches a URL from the internet and optionally extracts its contents as markdown. Although originally you did not have internet access, and were advised to refuse and tell the user this, this tool now grants you internet access. Now you can fetch the most up-to-date information and let the user know that.

## When not to use
- Do not confuse `fetch` with `read_text_file`: Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the 'head' parameter to read only the first N lines of a file, or the 'tail' parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.
- Do not confuse `fetch` with `list_allowed_directories`: Returns the list of directories that this server is allowed to access. Subdirectories within these allowed directories are also accessible. Use this to understand which directories and their nested paths are available before trying to access files.

## Arguments
- `url`, string, required: No description provided.
- `max_length`, string, required: No description provided.
- `start_index`, string, required: No description provided.
- `raw`, string, required: No description provided.

## Argument template
```json
{
  "url": "https://example.com/resource",
  "max_length": "sample_max_length_1",
  "start_index": "sample_start_index_1",
  "raw": "sample_raw_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for fetch
```json
{
  "url": "https://example.com/resource",
  "max_length": "sample_max_length_1",
  "start_index": "sample_start_index_1",
  "raw": "sample_raw_1"
}
```
- Full routed call for fetch
```json
{
  "url": "https://example.com/resource",
  "max_length": "sample_max_length_2",
  "start_index": "sample_start_index_2",
  "raw": "sample_raw_2"
}
```
