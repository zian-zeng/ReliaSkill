# tavily-crawl

**Condition:** `multi_candidate_skill`

## Summary
A powerful web crawler that initiates a structured web crawl starting from a specified base URL. The crawler expands from that point like a tree, following internal links across pages. You can control how deep and wide it goes, and.

## When to use
- Use `tavily-crawl` when the user's request directly matches this tool's purpose.
- Provide the required field `url`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `extract_depth`: 'basic', 'advanced'.
- Do not use when required inputs are missing.

## Arguments
- `url`, string, required: The root URL to begin the crawl
- `max_depth`, integer, optional, default=1: Max depth of the crawl. Defines how far from the base URL the crawler can explore.
- `max_breadth`, integer, optional, default=20: Max number of links to follow per level of the tree (i.e., per page)
- `limit`, integer, optional, default=50: Total number of links the crawler will process before stopping
- `instructions`, string, optional: Natural language instructions for the crawler
- `select_paths`, array, optional, default=[]: Regex patterns to select only URLs with specific path patterns (e.g., /docs/.*, /api/v1.*)
- `select_domains`, array, optional, default=[]: Regex patterns to select crawling to specific domains or subdomains (e.g., ^docs\.example\.com$)
- `allow_external`, boolean, optional, default=False: Whether to allow following links that go to external domains
- `categories`, array, optional, default=[]: Filter URLs using predefined categories like documentation, blog, api, etc
- `extract_depth`, string, optional, enum=['basic', 'advanced'], default='basic': Advanced extraction retrieves more data, including tables and embedded content, with higher success but may increase latency
- `format`, string, optional, enum=['markdown', 'text'], default='markdown': The format of the extracted web page content. markdown returns content in markdown format. text returns plain text and may increase latency.

## Argument template
```json
{
  "url": "https://example.com/resource",
  "max_depth": 1,
  "max_breadth": 20,
  "limit": 50,
  "instructions": "sample_instructions_1",
  "select_paths": [],
  "select_domains": [],
  "allow_external": false,
  "categories": [],
  "extract_depth": "basic",
  "format": "markdown"
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for tavily-crawl
```json
{
  "url": "https://example.com/resource"
}
```
- Richer invocation that uses optional controls for tavily-crawl
```json
{
  "url": "https://example.com/resource",
  "max_depth": 1,
  "max_breadth": 20,
  "limit": 50,
  "instructions": "sample_instructions_2",
  "select_paths": [],
  "select_domains": [],
  "allow_external": false,
  "categories": [],
  "extract_depth": "basic",
  "format": "markdown"
}
```
