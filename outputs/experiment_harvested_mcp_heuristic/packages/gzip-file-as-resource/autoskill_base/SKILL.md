# gzip-file-as-resource

**Condition:** `autoskill_base`

## Summary
Compresses a single file using gzip compression. Depending upon the selected output type, returns either the compressed data as a gzipped resource or a resource link, allowing it to be downloaded in a subsequent request during the current session. Provide all required fields: `name`, `data`, and `outputType`.

## When to use
- Use `gzip-file-as-resource` when the user's request directly matches this tool's purpose.
- Provide all required fields: `name`, `data`, and `outputType`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

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
- Minimal valid request that satisfies the required fields for gzip-file-as-resource
```json
{
  "name": "sample-name",
  "data": "sample_data_1",
  "outputType": "sample_outputType_1"
}
```
- Richer invocation that uses optional controls for gzip-file-as-resource
```json
{
  "name": "sample-name",
  "data": "sample_data_2",
  "outputType": "sample_outputType_2"
}
```
