# gzip-file-as-resource

**Condition:** `retrieved_candidates`

## Summary
Candidate retrieval ranked `gzip-file-as-resource` over nearby tools using cues like gzip-file-as-resource, compresses, using, gzip.

## When to use
- Retrieve a shortlist of nearby tools first, then choose `gzip-file-as-resource` when the request matches its role.
- Shortlist: gzip-file-as-resource, read_text_file, trigger-sampling-request-async.
- Compresses a single file using gzip compression. Depending upon the selected output type, returns either the compressed data as a gzipped resource or a resource link, allowing it to be downloaded in a subsequent request during the current session.
- Compresses a single file using gzip compression. Depending upon the selected output type, returns either the compressed data as a gzipped resource or a resource link, allowing it to be downloaded in a subsequent request during the current session.

## When not to use
- Do not confuse `gzip-file-as-resource` with `read_text_file`: Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the 'head' parameter to read only the first N lines of a file, or the 'tail' parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.
- Do not confuse `gzip-file-as-resource` with `trigger-sampling-request-async`: Trigger an async sampling request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends a request and the client executes it asynchronously, allowing the server to poll for progress and results.

## Arguments
- `name`, string, required: No description provided.
- `data`, string, required: No description provided.
- `outputType`, string, required: No description provided.

## Argument template
```json
{
  "name": "sample-name",
  "data": "sample_data_1",
  "outputType": "sample_outputType_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal routed call for gzip-file-as-resource
```json
{
  "name": "sample-name",
  "data": "sample_data_1",
  "outputType": "sample_outputType_1"
}
```
- Full routed call for gzip-file-as-resource
```json
{
  "name": "sample-name",
  "data": "sample_data_2",
  "outputType": "sample_outputType_2"
}
```
