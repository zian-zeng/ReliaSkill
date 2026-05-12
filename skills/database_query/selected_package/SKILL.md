# database.query

**Condition:** `multi_candidate_skill`

## Summary
Query the database based on certain conditions. Provide all required fields: `table`, and `conditions`.

## When to use
- Use `database.query` when the user's request directly matches this tool's purpose.
- Provide all required fields: `table`, and `conditions`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `table`, string, required: Name of the table to query.
- `conditions`, array, required: Conditions for the query.

## Argument template
```json
{
  "table": "sample_table_4",
  "conditions": [
    null
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for database.query
```json
{
  "table": "sample_table_1",
  "conditions": [
    null
  ]
}
```
- Richer invocation that uses optional controls for database.query
```json
{
  "table": "sample_table_2",
  "conditions": [
    null
  ]
}
```
- Required-argument dev behavior example.
```json
{
  "table": "sample_table_3",
  "conditions": [
    null
  ]
}
```
- Optional, enum, nested, or array argument example.
```json
{
  "table": "sample_table_4",
  "conditions": [
    null
  ]
}
```
