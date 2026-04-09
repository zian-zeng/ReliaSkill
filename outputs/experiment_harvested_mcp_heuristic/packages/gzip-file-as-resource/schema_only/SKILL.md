# gzip-file-as-resource

**Condition:** `schema_only`

## Summary
Compresses a single file using gzip compression. Depending upon the selected output type, returns either the compressed data as a gzipped resource or a resource link, allowing it to be downloaded in a subsequent request during the current session.

## When to use
- Use this normalized schema view when you need a deterministic rendering of the MCP input contract.
- Follow the exact field names, required markers, defaults, and enums shown below.

## When not to use
- Do not treat this baseline as semantic guidance beyond the original schema.

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
- Minimal valid call for gzip-file-as-resource
```json
{
  "name": "sample-name",
  "data": "sample_data_1",
  "outputType": "sample_outputType_1"
}
```
- Schema-aligned full call for gzip-file-as-resource
```json
{
  "name": "sample-name",
  "data": "sample_data_2",
  "outputType": "sample_outputType_2"
}
```
