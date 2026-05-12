# fetch

**Condition:** `multi_candidate_skill`

## Summary
Fetches a URL from the internet and optionally extracts its contents as markdown. Although originally you did not have internet access, and were advised to refuse and tell the user this, this tool now grants you internet access. Now you.

## When to use
- Use `fetch` when the user's request directly matches this tool's purpose.
- Provide all required fields: `url`, `max_length`, `start_index`, and `raw`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

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
- Minimal valid request that satisfies the required fields for fetch
```json
{
  "url": "https://example.com/resource",
  "max_length": "sample_max_length_1",
  "start_index": "sample_start_index_1",
  "raw": "sample_raw_1"
}
```
- Richer invocation that uses optional controls for fetch
```json
{
  "url": "https://example.com/resource",
  "max_length": "sample_max_length_2",
  "start_index": "sample_start_index_2",
  "raw": "sample_raw_2"
}
```
