# Related Work And Baseline Mapping

This note maps the current ReliaSkill comparison ladder to prior work that is closest in spirit.

## Current Ladder

- `raw_mcp`
  Raw schema and documentation exposure with no normalization.
- `schema_only`
  Deterministic normalized schema package with no retrieval or semantic enrichment.
- `retrieved_docs`
  Retrieved documentation snippets baseline, closest to a lightweight Gorilla-style docs exposure.
- `retrieved_candidates`
  Candidate-tool retrieval baseline, closest to ToolLLM-style shortlist-and-route retrieval.
- `retrieved_memory`
  Skill-memory retrieval baseline inspired by HELPER and Voyager style example reuse.
- `generated_skill_base`
  Base generated skill package with semantic hints, richer examples, and validation-aware candidate selection. This is a comparison condition, not the full ReliaSkill method.

## Closest Papers

### API-Bank

- Citation target: Li et al., EMNLP 2023
- Link: https://aclanthology.org/2023.emnlp-main.187/
- Why it matters:
  Strong benchmark framing for tool-augmented LLMs and useful for evaluation discussion.

### Gorilla

- Link: https://arxiv.org/abs/2305.15334
- Why it matters:
  Closest prior baseline for retrieved raw API documentation at inference time.
- Current repo mapping:
  `retrieved_docs`

### ToolLLM / ToolBench

- Link: https://arxiv.org/abs/2307.16789
- Why it matters:
  Strong prior work on large tool corpora, candidate retrieval, and tool-use decision making.
- Current repo mapping:
  `retrieved_candidates`

### HELPER / Memory-Augmented Instructable Agents

- Link: https://openreview.net/forum?id=ogh9vskMDH
- Why it matters:
  Closest memory-style precedent for retrieving language-program or skill memories.
- Current repo mapping:
  `retrieved_memory`

### Voyager

- Link: https://openreview.net/forum?id=ehfRiF0R3a
- Why it matters:
  Important inspiration for persistent skill libraries and example reuse, even though it is not an MCP tool benchmark paper.
- Current repo mapping:
  `retrieved_memory`

## What Is Still Missing For A Stronger Paper

- A larger and more diverse MCP tool benchmark (in progress with external harvested corpus).
- More exhaustive ablations across different model families (Llama 3, Mistral, etc.).
- Significance-aware comparison on larger test splits.
