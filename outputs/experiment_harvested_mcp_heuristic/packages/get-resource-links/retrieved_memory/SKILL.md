# get-resource-links

**Condition:** `retrieved_memory`

## Summary
Returns up to ten resource links that reference different types of resources

## When to use
- Retrieve similar skill examples from memory before filling arguments.

## When not to use
- Do not assume retrieved memories are perfect; keep field names schema-faithful.
- Do not invent unsupported arguments when no compatible memory matches the tool.

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
- Minimal valid memory-backed call for get-resource-links
```json
{
  "count": "sample_count_1"
}
```
