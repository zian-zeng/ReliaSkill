# read_file

**Condition:** `autoskill_base`

## Summary
Read the complete contents of a file as text. DEPRECATED: Use read_text_file instead. Provide the required field `path`.

## When to use
- Use `read_file` when the user's request directly matches this tool's purpose.
- Provide the required field `path`.
- Optional controls include `tail`, `head`.
- Map common request paraphrases to schema-faithful arguments using the semantic hints and examples.
- Prefer the smallest valid call that still captures file type, directionality, or enum intent from the request.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not let semantic cues override explicit user-provided field values.

## Arguments
- `path`, string, required: No description provided.
- `tail`, number, optional: No description provided.
- `head`, number, optional: No description provided.

## Argument template
```json
{
  "path": "data/sample.txt",
  "tail": 1.0,
  "head": 1.0
}
```

## Semantic hints
```json
{
  "head": {
    "top": "__number__",
    "beginning": "__number__",
    "opening": "__number__",
    "start of": "__number__"
  },
  "tail": {
    "bottom": "__number__",
    "trailing": "__number__",
    "ending": "__number__",
    "end of": "__number__"
  }
}
```

## Examples
- Minimal valid request that satisfies the required fields for read_file
```json
{
  "path": "data/sample.txt"
}
```
- Richer invocation that uses optional controls for read_file
```json
{
  "path": "data/sample.txt",
  "tail": 2.0,
  "head": 2.0
}
```
