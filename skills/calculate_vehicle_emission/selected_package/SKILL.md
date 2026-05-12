# calculate_vehicle_emission

**Condition:** `multi_candidate_skill`

## Summary
Calculate the annual carbon emissions produced by a specific type of vehicle based on mileage. Provide all required fields: `vehicle_type`, and `miles_driven`.

## When to use
- Use `calculate_vehicle_emission` when the user's request directly matches this tool's purpose.
- Provide all required fields: `vehicle_type`, and `miles_driven`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `vehicle_type`, string, required: The type of vehicle. 'gas' refers to a gasoline vehicle, 'diesel' refers to a diesel vehicle, and 'EV' refers to an electric vehicle.
- `miles_driven`, integer, required: The number of miles driven per year.
- `emission_factor`, float, optional: Optional emission factor to calculate emissions, in g/mile. Default factor is 355.48.

## Argument template
```json
{
  "vehicle_type": "sample_vehicle_type_1",
  "miles_driven": 1,
  "emission_factor": null
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for calculate_vehicle_emission
```json
{
  "vehicle_type": "sample_vehicle_type_1",
  "miles_driven": 1
}
```
- Richer invocation that uses optional controls for calculate_vehicle_emission
```json
{
  "vehicle_type": "sample_vehicle_type_2",
  "miles_driven": 2,
  "emission_factor": null
}
```
