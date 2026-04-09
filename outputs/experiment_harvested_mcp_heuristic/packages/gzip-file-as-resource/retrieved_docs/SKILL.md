# gzip-file-as-resource

**Condition:** `retrieved_docs`

## Summary
Compresses a single file using gzip compression. Depending upon the selected output type, returns either the compressed data as a gzipped resource or a resource link, allowing it to be downloaded in a subsequent request during the current session. GZip File as Resource Tool

## When to use
- Compresses a single file using gzip compression. Depending upon the selected output type, returns either the compressed data as a gzipped resource or a resource link, allowing it to be downloaded in a subsequent request during the current session.
- GZip File as Resource Tool
- data required
- outputType required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for gzip-file-as-resource
```json
{
  "name": "sample-name",
  "data": "sample_data_1",
  "outputType": "sample_outputType_1"
}
```
- Retrieved-docs fuller call for gzip-file-as-resource
```json
{
  "name": "sample-name",
  "data": "sample_data_2",
  "outputType": "sample_outputType_2"
}
```
