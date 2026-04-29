# Human Skill Authoring Packet

Tool id: `safe_synthetic_mcp_like_controls::mock_cloud_storage_mock_list_objects_044`
Tool name: `mock_cloud_storage_mock_list_objects_044`
Token budget: `300` approximate tokens.

Write exactly two files in `data/human_skills/skills/safe_synthetic_mcp_like_controls__mock_cloud_storage_mock_list_objects_044/`:

- `SKILL.md`
- `metadata.json`

Do not use dev/test controls, gold outputs, model predictions, or evaluation logs while authoring.

## Allowed SKILL.md Format

````markdown
# Tool name

## Summary
One compact paragraph describing when this tool is appropriate.

## When to use
- Direct usage boundary.
- Required information boundary.

## When not to use
- Adjacent or near-miss boundary.
- Missing required information boundary.

## Argument template
```json
{"field_name": "example value"}
```

## Examples
```json
{"arguments": {"field_name": "example value"}}
```
````

The formatting example above is not a task label and does not reveal gold outputs.

## Safety Notes

- Side-effect type: `read`.
- Require explicit user intent for write/delete/execute behavior.
- Do not invent missing required fields.
- Do not mention unsupported arguments or enum values.
- Prefer abstention for ambiguous adjacent-tool requests.
