# fetch

**Condition:** `retrieved_memory`

## Summary
Fetches a URL from the internet and optionally extracts its contents as markdown. Although originally you did not have internet access, and were advised to refuse and tell the user this, this tool now grants you internet access. Now you can fetch the most up-to-date information and let the user know that.

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

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
- Minimal valid memory-backed call for fetch
```json
{
  "url": "https://example.com/resource",
  "max_length": "sample_max_length_1",
  "start_index": "sample_start_index_1",
  "raw": "sample_raw_1"
}
```
