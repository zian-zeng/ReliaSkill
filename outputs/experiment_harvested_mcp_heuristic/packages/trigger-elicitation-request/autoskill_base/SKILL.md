# trigger-elicitation-request

**Condition:** `autoskill_base`

## Summary
Trigger a Request from the Server for User Elicitation. This tool has no required input fields.

## When to use
- Use `trigger-elicitation-request` when the user's request directly matches this tool's purpose.
- This tool has no required input fields.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Tool does not expose top-level input properties.
- Do not let semantic cues override explicit user-provided field values.

## Arguments
- This tool does not expose structured input arguments.

## Argument template
This condition does not add a normalized argument template beyond the raw schema.

## Semantic hints
No explicit semantic hints for this condition.

## Examples
No synthesized examples for this condition.
