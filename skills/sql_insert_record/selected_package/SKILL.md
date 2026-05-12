# sql_insert_record

**Condition:** `multi_candidate_skill`

## Summary
API-Bank-style local fixture database tool that inserts a structured record into a mock table. Provide all required fields: `database`, `table`, and `record`.

## When to use
- Use `sql_insert_record` when the user's request directly matches this tool's purpose.
- Provide all required fields: `database`, `table`, and `record`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `conflict_policy`: 'error', 'ignore', 'update'.
- Do not use when required inputs are missing.

## Arguments
- `database`, string, required: Fixture database name.
- `table`, string, required: Mock table name.
- `record`, object, required: Record fields to insert.
- `conflict_policy`, string, optional, enum=['error', 'ignore', 'update']: Conflict handling policy.

## Argument template
```json
{
  "database": "sample_database_1",
  "table": "sample_table_1",
  "record": {},
  "conflict_policy": "error"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for sql_insert_record
```json
{
  "database": "sample_database_1",
  "table": "sample_table_1",
  "record": {}
}
```
- Richer invocation that uses optional controls for sql_insert_record
```json
{
  "database": "sample_database_2",
  "table": "sample_table_2",
  "record": {},
  "conflict_policy": "ignore"
}
```
