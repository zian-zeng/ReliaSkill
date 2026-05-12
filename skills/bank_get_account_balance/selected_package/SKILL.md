# bank_get_account_balance

**Condition:** `multi_candidate_skill`

## Summary
API-Bank-style local fixture tool for retrieving the balance and currency of a mock bank account without contacting external services. Provide the required field `account_id`.

## When to use
- Use `bank_get_account_balance` when the user's request directly matches this tool's purpose.
- Provide the required field `account_id`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `account_id`, string, required: Mock account identifier.
- `include_pending`, boolean, optional: Whether pending transactions should be included.

## Argument template
```json
{
  "account_id": "sample-account-id-001",
  "include_pending": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for bank_get_account_balance
```json
{
  "account_id": "sample-account-id-001"
}
```
- Richer invocation that uses optional controls for bank_get_account_balance
```json
{
  "account_id": "sample-account-id-001",
  "include_pending": true
}
```
