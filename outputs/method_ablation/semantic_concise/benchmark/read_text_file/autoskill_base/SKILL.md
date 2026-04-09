# read_text_file

**Condition:** `autoskill_base`

## Summary
Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the head parameter to read only the first N lines of a file, or the tail parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories. Provide the required field `path`.

## When to use
- Use `read_text_file` when the user's request directly matches this tool's purpose.
- Provide the required field `path`.
- Optional controls include `tail`, `head`.
- Use the semantic hints when the request uses paraphrases rather than exact schema wording.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `path`, string, required: Path to the file within an allowed directory.
- `tail`, number, optional: If provided, returns only the last N lines of the file.
- `head`, number, optional: If provided, returns only the first N lines of the file.

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
- Minimal valid request that satisfies the required fields for read_text_file
```json
{
  "path": "data/sample.txt"
}
```
- Richer invocation that uses optional controls for read_text_file
```json
{
  "path": "data/sample.txt",
  "tail": 2.0,
  "head": 2.0
}
```
