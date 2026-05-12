# playwright_save_as_pdf

**Condition:** `multi_candidate_skill`

## Summary
Save the current page as a PDF file. Provide the required field `outputPath`.

## When to use
- Use `playwright_save_as_pdf` when the user's request directly matches this tool's purpose.
- Provide the required field `outputPath`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `outputPath`, string, required: Directory path where PDF will be saved
- `filename`, string, optional: Name of the PDF file (default: page.pdf)
- `format`, string, optional: Page format (e.g. 'A4', 'Letter')
- `printBackground`, boolean, optional: Whether to print background graphics
- `margin`, object, optional: Page margins

## Argument template
```json
{
  "outputPath": "data/sample.txt",
  "filename": "data/sample.txt",
  "format": "sample_format_1",
  "printBackground": false,
  "margin": {
    "bottom": "sample_bottom_1",
    "left": "sample_left_1",
    "right": "sample_right_1",
    "top": "sample_top_1"
  }
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for playwright_save_as_pdf
```json
{
  "outputPath": "data/sample.txt"
}
```
- Richer invocation that uses optional controls for playwright_save_as_pdf
```json
{
  "outputPath": "data/sample.txt",
  "filename": "data/sample.txt",
  "format": "sample_format_2",
  "printBackground": true,
  "margin": {
    "bottom": "sample_bottom_2",
    "left": "sample_left_2",
    "right": "sample_right_2",
    "top": "sample_top_2"
  }
}
```
