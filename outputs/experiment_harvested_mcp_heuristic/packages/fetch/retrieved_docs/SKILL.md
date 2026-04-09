# fetch

**Condition:** `retrieved_docs`

## Summary
Fetches a URL from the internet and optionally extracts its contents as markdown. Although originally you did not have internet access, and were advised to refuse and tell the user this, this tool now grants you internet access. Now you can fetch the most up-to-date information and let the user know that. fetch

## When to use
- Fetches a URL from the internet and optionally extracts its contents as markdown. Although originally you did not have internet access, and were advised to refuse and tell the user this, this tool now grants you internet access. Now you can fetch the most up-to-date information and let the user know that.
- fetch
- url required
- start_index required

## When not to use
- Do not assume capabilities beyond the retrieved tool documentation.

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
- Retrieved-docs minimal call for fetch
```json
{
  "url": "https://example.com/resource",
  "max_length": "sample_max_length_1",
  "start_index": "sample_start_index_1",
  "raw": "sample_raw_1"
}
```
- Retrieved-docs fuller call for fetch
```json
{
  "url": "https://example.com/resource",
  "max_length": "sample_max_length_2",
  "start_index": "sample_start_index_2",
  "raw": "sample_raw_2"
}
```
