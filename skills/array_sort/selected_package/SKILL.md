# array_sort

**Condition:** `multi_candidate_skill`

## Summary
Sorts a given list in ascending or descending order. Provide all required fields: `list`, and `order`.

## When to use
- Use `array_sort` when the user's request directly matches this tool's purpose.
- Provide all required fields: `list`, and `order`.
- Use only when the request clearly needs `array_sort`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `order`: 'ascending', 'descending'.
- Do not use for adjacent tools with similar names, descriptions, or arguments.
- Do not use for read/write, search/fetch, create/update, delete/preview, or execute/explain mismatches.
- If the request lacks required fields, abstain or ask for clarification.

## Arguments
- `list`, array, required: The list of numbers to be sorted.
- `order`, string, required, enum=['ascending', 'descending']: Order of sorting. If not specified, it will default to ascending.

## Argument template
```json
{
  "list": [
    null
  ],
  "order": "ascending"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for array_sort
```json
{
  "list": [
    null
  ],
  "order": "ascending"
}
```
- Richer invocation that uses optional controls for array_sort
```json
{
  "list": [
    null
  ],
  "order": "descending"
}
```
