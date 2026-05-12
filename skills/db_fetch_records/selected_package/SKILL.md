# db_fetch_records

**Condition:** `multi_candidate_skill`

## Summary
Fetch records from a specified database table based on certain conditions. Provide all required fields: `database_name`, `table_name`, and `conditions`.

## When to use
- Use `db_fetch_records` when the user's request directly matches this tool's purpose.
- Provide all required fields: `database_name`, `table_name`, and `conditions`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `database_name`, string, required: The name of the database.
- `table_name`, string, required: The name of the table from which records need to be fetched.
- `conditions`, dict, required: The conditions based on which records are to be fetched.
- `fetch_limit`, integer, optional: Limits the number of records to be fetched. If left empty, it fetches all records. (Optional) Default is 0.

## Argument template
```json
{
  "database_name": "sample-name",
  "table_name": "sample-name",
  "conditions": null,
  "fetch_limit": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for db_fetch_records
```json
{
  "database_name": "sample-name",
  "table_name": "sample-name",
  "conditions": null
}
```
- Richer invocation that uses optional controls for db_fetch_records
```json
{
  "database_name": "sample-name",
  "table_name": "sample-name",
  "conditions": null,
  "fetch_limit": 2
}
```
