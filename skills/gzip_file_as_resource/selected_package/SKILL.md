# gzip-file-as-resource

**Condition:** `multi_candidate_skill`

## Summary
Compresses a single file using gzip compression. Depending upon the selected output type, returns either the compressed data as a gzipped resource or a resource link, allowing it to be downloaded in a subsequent request during the current session. This.

## When to use
- Use `gzip-file-as-resource` when the user's request directly matches this tool's purpose.
- This tool has no required input fields.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `name`, string, optional: No description provided.
- `data`, string, optional: No description provided.
- `outputType`, string, optional: No description provided.

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
- Richer invocation that uses optional controls for gzip-file-as-resource
```json
{
  "name": "sample-name",
  "data": "sample_data_2",
  "outputType": "sample_outputType_2"
}
```
