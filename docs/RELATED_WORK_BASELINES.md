# Related Work And Baseline Mapping

This note maps the ReliaSkill paper conditions and auxiliary codebase baselines to nearby tool-use and skill-library research.

## Reported Conditions

- `raw_mcp`
  Raw MCP-style tool record with schema and sparse documentation.
- `generated_skill_base`
  Generated skill artifact with semantic guidance but without the stronger boundary-first reliability contract.
- `curated_schema_reference`
  Schema-normalized reference condition used to isolate the effect of faithful schemas from skill-style guidance.
- `skill_prompt_boundary_first`
  Boundary-first ReliaSkill condition emphasizing when-to-use, when-not-to-use, valid arguments, and abstention behavior.
- `skill_prompt_verbose_docs`
  Verbose ReliaSkill condition with expanded documentation and examples.

## Auxiliary Baselines In The Codebase

Some scripts also support retrieval- and memory-style variants that are useful for ablations but are not the headline five-condition result table:

- `schema_only`
  Deterministic normalized schema package with no semantic enrichment.
- `retrieved_docs`
  Retrieved documentation snippets, closest to a lightweight Gorilla-style documentation exposure.
- `retrieved_candidates`
  Candidate-tool retrieval, closest to ToolLLM / ToolBench-style shortlist-and-route evaluation.
- `retrieved_memory`
  Retrieved skill-memory examples, inspired by HELPER and Voyager-style example reuse.

## Closest Papers

### API-Bank

- Citation target: Li et al., EMNLP 2023
- Link: https://aclanthology.org/2023.emnlp-main.187/
- Relevance: benchmark framing for tool-augmented LLM evaluation.

### Gorilla

- Link: https://arxiv.org/abs/2305.15334
- Relevance: retrieved raw API documentation at inference time.
- Codebase mapping: `retrieved_docs`

### ToolLLM / ToolBench

- Link: https://arxiv.org/abs/2307.16789
- Relevance: large tool corpora, candidate retrieval, and tool-use decision making.
- Codebase mapping: `retrieved_candidates`

### HELPER / Memory-Augmented Instructable Agents

- Link: https://openreview.net/forum?id=ogh9vskMDH
- Relevance: retrieving language-program or skill memories.
- Codebase mapping: `retrieved_memory`

### Voyager

- Link: https://openreview.net/forum?id=ehfRiF0R3a
- Relevance: persistent skill libraries and example reuse, although it is not an MCP tool benchmark.
- Codebase mapping: `retrieved_memory`

## Extensions

The main paper emphasizes cold-start reliability before live server execution. Natural extensions include larger live-MCP server execution studies, broader proprietary and open-model coverage, and significance analysis over larger benchmark slices.
