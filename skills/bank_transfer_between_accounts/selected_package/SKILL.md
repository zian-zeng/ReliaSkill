# bank_transfer_between_accounts

**Condition:** `multi_candidate_skill`

## Summary
API-Bank-style local fixture tool that records a mock transfer between two fixture accounts. Provide all required fields: `source_account_id`, `destination_account_id`, and `amount`.

## When to use
- Use `bank_transfer_between_accounts` when the user's request directly matches this tool's purpose.
- Provide all required fields: `source_account_id`, `destination_account_id`, and `amount`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `source_account_id`, string, required: Mock source account identifier.
- `destination_account_id`, string, required: Mock destination account identifier.
- `amount`, number, required: Transfer amount.
- `memo`, string, optional: Optional transfer memo.
- `dry_run`, boolean, optional: Validate without recording the transfer.

## Argument template
```json
{
  "source_account_id": "sample-source-account-id-001",
  "destination_account_id": "sample-destination-account-id-001",
  "amount": 1.0,
  "memo": "sample_memo_1",
  "dry_run": false
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for bank_transfer_between_accounts
```json
{
  "source_account_id": "sample-source-account-id-001",
  "destination_account_id": "sample-destination-account-id-001",
  "amount": 1.0
}
```
- Richer invocation that uses optional controls for bank_transfer_between_accounts
```json
{
  "source_account_id": "sample-source-account-id-001",
  "destination_account_id": "sample-destination-account-id-001",
  "amount": 2.0,
  "memo": "sample_memo_2",
  "dry_run": true
}
```
