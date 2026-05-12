# bank_search_transactions

**Condition:** `multi_candidate_skill`

## Summary
API-Bank-style local fixture tool for searching transactions by date, category, and amount range. Provide the required field `account_id`.

## When to use
- Use `bank_search_transactions` when the user's request directly matches this tool's purpose.
- Provide the required field `account_id`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `category`: 'food', 'travel', 'utilities', 'income'.
- Do not use when required inputs are missing.

## Arguments
- `account_id`, string, required: Mock account identifier.
- `date_range`, object, optional: Inclusive date range.
- `category`, string, optional, enum=['food', 'travel', 'utilities', 'income']: Transaction category.
- `limit`, integer, optional: Maximum results.

## Argument template
```json
{
  "account_id": "sample-account-id-001",
  "date_range": {
    "end": "2026-01-01",
    "start": "2026-01-01"
  },
  "category": "food",
  "limit": 1
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for bank_search_transactions
```json
{
  "account_id": "sample-account-id-001"
}
```
- Richer invocation that uses optional controls for bank_search_transactions
```json
{
  "account_id": "sample-account-id-001",
  "date_range": {
    "end": "2026-01-01",
    "start": "2026-01-01"
  },
  "category": "travel",
  "limit": 2
}
```
