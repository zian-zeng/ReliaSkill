# employee.fetch_data

**Condition:** `multi_candidate_skill`

## Summary
Fetches the detailed data for a specific employee in a given company. Provide all required fields: `company_name`, and `employee_id`.

## When to use
- Use `employee.fetch_data` when the user's request directly matches this tool's purpose.
- Provide all required fields: `company_name`, and `employee_id`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `company_name`, string, required: The name of the company.
- `employee_id`, integer, required: The unique ID of the employee.
- `data_field`, array, optional: Fields of data to be fetched for the employee (Optional). Default is ['Personal Info']

## Argument template
```json
{
  "company_name": "sample-name",
  "employee_id": 1,
  "data_field": [
    "sample_data_field_item_1"
  ]
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for employee.fetch_data
```json
{
  "company_name": "sample-name",
  "employee_id": 1
}
```
- Richer invocation that uses optional controls for employee.fetch_data
```json
{
  "company_name": "sample-name",
  "employee_id": 2,
  "data_field": [
    "sample_data_field_item_2"
  ]
}
```
