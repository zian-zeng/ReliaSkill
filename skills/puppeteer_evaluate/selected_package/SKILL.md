# puppeteer_evaluate

**Condition:** `multi_candidate_skill`

## Summary
Execute JavaScript in the browser console. Provide the required field `script`.

## When to use
- Use `puppeteer_evaluate` when the user's request directly matches this tool's purpose.
- Provide the required field `script`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `script`, string, required: JavaScript code to execute

## Argument template
```json
{
  "script": "sample_script_4"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for puppeteer_evaluate
```json
{
  "script": "sample_script_1"
}
```
- Richer invocation that uses optional controls for puppeteer_evaluate
```json
{
  "script": "sample_script_2"
}
```
- Required-argument dev behavior example.
```json
{
  "script": "sample_script_3"
}
```
- Optional, enum, nested, or array argument example.
```json
{
  "script": "sample_script_4"
}
```
