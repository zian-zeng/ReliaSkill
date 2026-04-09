# get-resource-links

**Condition:** `autoskill_base`

## Summary
Returns up to ten resource links that reference different types of resources. Provide the required field `count`.

## When to use
- Use `get-resource-links` when the user's request directly matches this tool's purpose.
- Provide the required field `count`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

## Arguments
- `count`, string, required: No description provided.

## Argument template
```json
{
  "count": "sample_count_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for get-resource-links
```json
{
  "count": "sample_count_1"
}
```
- Richer invocation that uses optional controls for get-resource-links
```json
{
  "count": "sample_count_2"
}
```
