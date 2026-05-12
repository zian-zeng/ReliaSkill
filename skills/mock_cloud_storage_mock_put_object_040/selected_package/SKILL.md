# mock_cloud_storage_mock_put_object_040

**Condition:** `multi_candidate_skill`

## Summary
Synthetic safe mock cloud-storage write tool for an offline bucket fixture. Provide all required fields: `bucket`, and `key`.

## When to use
- Use `mock_cloud_storage_mock_put_object_040` when the user's request directly matches this tool's purpose.
- Provide all required fields: `bucket`, and `key`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `bucket`, string, required: Mock bucket name.
- `key`, string, required: Object key.
- `metadata`, object, optional: Object metadata.
- `dry_run`, boolean, optional: When true, validate the request without changing the mock system.

## Argument template
```json
{
  "bucket": "sample_bucket_1",
  "key": "sample_key_1",
  "metadata": {
    "cache_control": "sample_cache_control_1",
    "content_type": "sample_content_type_1"
  },
  "dry_run": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for mock_cloud_storage_mock_put_object_040
```json
{
  "bucket": "sample_bucket_1",
  "key": "sample_key_1"
}
```
- Richer invocation that uses optional controls for mock_cloud_storage_mock_put_object_040
```json
{
  "bucket": "sample_bucket_2",
  "key": "sample_key_2",
  "metadata": {
    "cache_control": "sample_cache_control_2",
    "content_type": "sample_content_type_2"
  },
  "dry_run": true
}
```
