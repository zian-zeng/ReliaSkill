# tavily-map

**Condition:** `multi_candidate_skill`

## Summary
A powerful web mapping tool that creates a structured map of website URLs, allowing you to discover and analyze site structure, content organization, and navigation paths. Perfect for site audits, content discovery, and understanding website architecture. Provide the required field.

## When to use
- Use `tavily-map` when the user's request directly matches this tool's purpose.
- Provide the required field `url`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Do not use when required inputs are missing.

## Arguments
- `url`, string, required: The root URL to begin the mapping
- `max_depth`, integer, optional, default=1: Max depth of the mapping. Defines how far from the base URL the crawler can explore
- `max_breadth`, integer, optional, default=20: Max number of links to follow per level of the tree (i.e., per page)
- `limit`, integer, optional, default=50: Total number of links the crawler will process before stopping
- `instructions`, string, optional: Natural language instructions for the crawler
- `select_paths`, array, optional, default=[]: Regex patterns to select only URLs with specific path patterns (e.g., /docs/.*, /api/v1.*)
- `select_domains`, array, optional, default=[]: Regex patterns to select crawling to specific domains or subdomains (e.g., ^docs\.example\.com$)
- `allow_external`, boolean, optional, default=False: Whether to allow following links that go to external domains
- `categories`, array, optional, default=[]: Filter URLs using predefined categories like documentation, blog, api, etc

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
  "categories": []
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for tavily-map
```json
{
  "url": "https://example.com/resource"
}
```
- Richer invocation that uses optional controls for tavily-map
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
  "categories": []
}
```
