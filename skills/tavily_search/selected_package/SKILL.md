# tavily-search

**Condition:** `multi_candidate_skill`

## Summary
A powerful web search tool that provides comprehensive, real-time results using Tavily's AI search engine. Returns relevant web content with customizable parameters for result count, content type, and domain filtering. Ideal for gathering current information, news, and detailed web content.

## When to use
- Use `tavily-search` when the user's request directly matches this tool's purpose.
- Provide the required field `query`.

## When not to use
- Do not call this tool when required inputs are missing or ambiguous.
- Do not invent unsupported parameters or unsupported enum values.
- Respect the allowed values for `search_depth`: 'basic', 'advanced'.
- Do not use when required inputs are missing.

## Arguments
- `query`, string, required: Search query
- `search_depth`, string, optional, enum=['basic', 'advanced'], default='basic': The depth of the search. It can be 'basic' or 'advanced'
- `topic`, string, optional, enum=['general', 'news'], default='general': The category of the search. This will determine which of our agents will be used for the search
- `days`, number, optional, default=3: The number of days back from the current date to include in the search results. This specifies the time frame of data to be retrieved. Please note that this feature is only available when using the 'news' search topic
- `time_range`, string, optional, enum=['day', 'week', 'month', 'year', 'd', 'w', 'm', 'y']: The time range back from the current date to include in the search results. This feature is available for both 'general' and 'news' search topics
- `max_results`, number, optional, default=10: The maximum number of search results to return
- `include_images`, boolean, optional, default=False: Include a list of query-related images in the response
- `include_image_descriptions`, boolean, optional, default=False: Include a list of query-related images and their descriptions in the response
- `include_raw_content`, boolean, optional, default=False: Include the cleaned and parsed HTML content of each search result
- `include_domains`, array, optional, default=[]: A list of domains to specifically include in the search results, if the user asks to search on specific sites set this to the domain of the site
- `exclude_domains`, array, optional, default=[]: List of domains to specifically exclude, if the user asks to exclude a domain set this to the domain of the site
- `country`, string, optional, enum=['afghanistan', 'albania', 'algeria', 'andorra', 'angola', 'argentina', 'armenia', 'australia', 'austria', 'azerbaijan', 'bahamas', 'bahrain', 'bangladesh', 'barbados', 'belarus', 'belgium', 'belize', 'benin', 'bhutan', 'bolivia', 'bosnia and herzegovina', 'botswana', 'brazil', 'brunei', 'bulgaria', 'burkina faso', 'burundi', 'cambodia', 'cameroon', 'canada', 'cape verde', 'central african republic', 'chad', 'chile', 'china', 'colombia', 'comoros', 'congo', 'costa rica', 'croatia', 'cuba', 'cyprus', 'czech republic', 'denmark', 'djibouti', 'dominican republic', 'ecuador', 'egypt', 'el salvador', 'equatorial guinea', 'eritrea', 'estonia', 'ethiopia', 'fiji', 'finland', 'france', 'gabon', 'gambia', 'georgia', 'germany', 'ghana', 'greece', 'guatemala', 'guinea', 'haiti', 'honduras', 'hungary', 'iceland', 'india', 'indonesia', 'iran', 'iraq', 'ireland', 'israel', 'italy', 'jamaica', 'japan', 'jordan', 'kazakhstan', 'kenya', 'kuwait', 'kyrgyzstan', 'latvia', 'lebanon', 'lesotho', 'liberia', 'libya', 'liechtenstein', 'lithuania', 'luxembourg', 'madagascar', 'malawi', 'malaysia', 'maldives', 'mali', 'malta', 'mauritania', 'mauritius', 'mexico', 'moldova', 'monaco', 'mongolia', 'montenegro', 'morocco', 'mozambique', 'myanmar', 'namibia', 'nepal', 'netherlands', 'new zealand', 'nicaragua', 'niger', 'nigeria', 'north korea', 'north macedonia', 'norway', 'oman', 'pakistan', 'panama', 'papua new guinea', 'paraguay', 'peru', 'philippines', 'poland', 'portugal', 'qatar', 'romania', 'russia', 'rwanda', 'saudi arabia', 'senegal', 'serbia', 'singapore', 'slovakia', 'slovenia', 'somalia', 'south africa', 'south korea', 'south sudan', 'spain', 'sri lanka', 'sudan', 'sweden', 'switzerland', 'syria', 'taiwan', 'tajikistan', 'tanzania', 'thailand', 'togo', 'trinidad and tobago', 'tunisia', 'turkey', 'turkmenistan', 'uganda', 'ukraine', 'united arab emirates', 'united kingdom', 'united states', 'uruguay', 'uzbekistan', 'venezuela', 'vietnam', 'yemen', 'zambia', 'zimbabwe'], default='': Boost search results from a specific country. This will prioritize content from the selected country in the search results. Available only if topic is general.

## Argument template
```json
{
  "query": "sample query",
  "search_depth": "basic",
  "topic": "general",
  "days": 3,
  "time_range": "day",
  "max_results": 10,
  "include_images": false,
  "include_image_descriptions": false,
  "include_raw_content": false,
  "include_domains": [],
  "exclude_domains": [],
  "country": ""
}
```

## Semantic hints
No explicit semantic hints for this condition.

## Examples
- Minimal valid request that satisfies the required fields for tavily-search
```json
{
  "query": "sample query"
}
```
- Richer invocation that uses optional controls for tavily-search
```json
{
  "query": "sample query",
  "search_depth": "basic",
  "topic": "general",
  "days": 3,
  "time_range": "week",
  "max_results": 10,
  "include_images": false,
  "include_image_descriptions": false,
  "include_raw_content": false,
  "include_domains": [],
  "exclude_domains": [],
  "country": ""
}
```
