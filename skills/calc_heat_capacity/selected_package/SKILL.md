# calc_heat_capacity

**Condition:** `multi_candidate_skill`

## Summary
Calculate the heat capacity at constant pressure of air using its temperature and volume. Provide all required fields: `temp`, and `volume`.

## When to use
- Use `calc_heat_capacity` when the user's request directly matches this tool's purpose.
- Provide all required fields: `temp`, and `volume`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `temp`, integer, required: The temperature of the gas in Kelvin.
- `volume`, integer, required: The volume of the gas in m^3.
- `gas`, string, optional: Type of gas, with air as default.

## Argument template
```json
{
  "temp": 1,
  "volume": 1,
  "gas": "sample_gas_1"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calc_heat_capacity
```json
{
  "temp": 1,
  "volume": 1
}
```
- Richer invocation that uses optional controls for calc_heat_capacity
```json
{
  "temp": 2,
  "volume": 2,
  "gas": "sample_gas_2"
}
```
