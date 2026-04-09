# trigger-elicitation-request-async

**Condition:** `autoskill_base`

## Summary
Trigger an async elicitation request that the CLIENT executes as a background task. Demonstrates bidirectional MCP tasks where the server sends an elicitation request and the client handles user input asynchronously, allowing the server to poll for completion. This tool has no required input fields.

## When to use
- Use `trigger-elicitation-request-async` when the user's request directly matches this tool's purpose.
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
