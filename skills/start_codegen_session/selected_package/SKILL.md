# start_codegen_session

**Condition:** `multi_candidate_skill`

## Summary
Start a new code generation session to record Playwright actions. Provide the required field `options`.

## When to use
- Use `start_codegen_session` when the user's request directly matches this tool's purpose.
- Provide the required field `options`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `options`, object, required: Code generation options

## Argument template
```json
{
  "options": {
    "includeComments": false,
    "outputPath": "data/sample.txt",
    "testNamePrefix": "sample-name"
  }
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for start_codegen_session
```json
{
  "options": {
    "includeComments": false,
    "outputPath": "data/sample.txt",
    "testNamePrefix": "sample-name"
  }
}
```
- Richer invocation that uses optional controls for start_codegen_session
```json
{
  "options": {
    "includeComments": true,
    "outputPath": "data/sample.txt",
    "testNamePrefix": "sample-name"
  }
}
```
