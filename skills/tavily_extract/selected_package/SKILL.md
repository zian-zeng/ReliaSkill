# tavily-extract

**Condition:** `multi_candidate_skill`

## Summary
A powerful web content extraction tool that retrieves and processes raw content from specified URLs, ideal for data collection, content analysis, and research tasks. Provide the required field `urls`.

## When to use
- Use `tavily-extract` when the user's request directly matches this tool's purpose.
- Provide the required field `urls`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `extract_depth`: 'basic', 'advanced'.
- Do not use when required inputs are missing.

## Arguments
- `urls`, array, required: List of URLs to extract content from
- `extract_depth`, string, optional, enum=['basic', 'advanced'], default='basic': Depth of extraction - 'basic' or 'advanced', if usrls are linkedin use 'advanced' or if explicitly told to use advanced
- `include_images`, boolean, optional, default=False: Include a list of images extracted from the urls in the response
- `format`, string, optional, enum=['markdown', 'text'], default='markdown': The format of the extracted web page content. markdown returns content in markdown format. text returns plain text and may increase latency.

## Argument template
```json
{
  "urls": [
    "https://example.com/resource"
  ],
  "extract_depth": "basic",
  "include_images": false,
  "format": "markdown"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for tavily-extract
```json
{
  "urls": [
    "https://example.com/resource"
  ]
}
```
- Richer invocation that uses optional controls for tavily-extract
```json
{
  "urls": [
    "https://example.com/resource"
  ],
  "extract_depth": "basic",
  "include_images": false,
  "format": "markdown"
}
```
