# get-resource-links

**Condition:** `multi_candidate_skill`

## Summary
Returns up to ten resource links that reference different types of resources. This tool has no required input fields.

## When to use
- Use `get-resource-links` when the user's request directly matches this tool's purpose.
- This tool has no required input fields.
- Optional control is available through `count` when the request needs extra specificity.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `count`, string, optional: No description provided.

## Argument template
```json
{
  "count": "sample_count_4"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Richer invocation that uses optional controls for get-resource-links
```json
{
  "count": "sample_count_2"
}
```
- Optional, enum, nested, or array argument example.
```json
{
  "count": "sample_count_4"
}
```
