# mock_cloud_storage_mock_list_objects_044

**Condition:** `multi_candidate_skill`

## Summary
Synthetic safe mock cloud-storage retrieval tool for listing fixture objects. Provide the required field `bucket`.

## When to use
- Use `mock_cloud_storage_mock_list_objects_044` when the user's request directly matches this tool's purpose.
- Provide the required field `bucket`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `bucket`, string, required: Mock bucket name.
- `prefix`, string, optional: Object key prefix.
- `include_metadata`, boolean, optional: Whether to include metadata.

## Argument template
```json
{
  "bucket": "sample_bucket_1",
  "prefix": "sample_prefix_1",
  "include_metadata": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for mock_cloud_storage_mock_list_objects_044
```json
{
  "bucket": "sample_bucket_1"
}
```
- Richer invocation that uses optional controls for mock_cloud_storage_mock_list_objects_044
```json
{
  "bucket": "sample_bucket_2",
  "prefix": "sample_prefix_2",
  "include_metadata": true
}
```
