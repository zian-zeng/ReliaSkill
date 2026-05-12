# sql_run_readonly_query

**Condition:** `multi_candidate_skill`

## Summary
API-Bank-style local fixture database tool that executes a readonly SQL query against a mock database. Provide all required fields: `database`, and `query`.

## When to use
- Use `sql_run_readonly_query` when the user's request directly matches this tool's purpose.
- Provide all required fields: `database`, and `query`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `database`, string, required: Fixture database name.
- `query`, string, required: Readonly SQL query.
- `parameters`, object, optional: Named query parameters.
- `limit`, integer, optional: Maximum rows.

## Argument template
```json
{
  "database": "sample_database_1",
  "query": "sample query",
  "parameters": {},
  "limit": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for sql_run_readonly_query
```json
{
  "database": "sample_database_1",
  "query": "sample query"
}
```
- Richer invocation that uses optional controls for sql_run_readonly_query
```json
{
  "database": "sample_database_2",
  "query": "sample query",
  "parameters": {},
  "limit": 2
}
```
