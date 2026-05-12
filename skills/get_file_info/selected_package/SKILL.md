# get_file_info

**Condition:** `multi_candidate_skill`

## Summary
Retrieve detailed metadata about a file or directory. Returns comprehensive information including size, creation time, last modified time, permissions, and type. This tool is perfect for understanding file characteristics without reading the actual content. Only works within allowed directories. Provide the required field `path`.

## When to use
- Use `get_file_info` when the user's request directly matches this tool's purpose.
- Provide the required field `path`.
- Use examples to map paraphrases into schema-faithful arguments.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.

## Arguments
- `path`, string, required: No description provided.

## Argument template
```json
{
  "path": "data/sample.txt"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for get_file_info
```json
{
  "path": "data/sample.txt"
}
```
- Richer invocation that uses optional controls for get_file_info
```json
{
  "path": "data/sample.txt"
}
```
- Required-argument dev behavior example.
```json
{
  "path": "data/sample.txt"
}
```
