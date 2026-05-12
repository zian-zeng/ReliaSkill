# storage_copy_object

**Condition:** `multi_candidate_skill`

## Summary
API-Bank-style local fixture cloud-storage tool for copying an object between offline buckets. Provide all required fields: `source`, and `destination`.

## When to use
- Use `storage_copy_object` when the user's request directly matches this tool's purpose.
- Provide all required fields: `source`, and `destination`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `source`, object, required: Source object.
- `destination`, object, required: Destination object.
- `overwrite`, boolean, optional: Whether to overwrite an existing mock object.

## Argument template
```json
{
  "source": {
    "bucket": "sample_bucket_1",
    "key": "sample_key_1"
  },
  "destination": {
    "bucket": "sample_bucket_1",
    "key": "sample_key_1"
  },
  "overwrite": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for storage_copy_object
```json
{
  "source": {
    "bucket": "sample_bucket_1",
    "key": "sample_key_1"
  },
  "destination": {
    "bucket": "sample_bucket_1",
    "key": "sample_key_1"
  }
}
```
- Richer invocation that uses optional controls for storage_copy_object
```json
{
  "source": {
    "bucket": "sample_bucket_2",
    "key": "sample_key_2"
  },
  "destination": {
    "bucket": "sample_bucket_2",
    "key": "sample_key_2"
  },
  "overwrite": true
}
```
