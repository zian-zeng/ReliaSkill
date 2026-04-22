# AutoSkill

AutoSkill is a Stage A prototype for converting raw MCP tool definitions into agent-ready skill packages and comparing them against simple baselines.

The current comparison ladder is:

- `raw_mcp`: raw schema and docs only
- `schema_only`: deterministic cleaned schema package
- `retrieved_docs`: Gorilla-style retrieved documentation snippets
- `retrieved_candidates`: ToolLLM-style candidate-tool retrieval baseline
- `retrieved_memory`: skill-memory retrieval baseline inspired by HELPER/Voyager
- `autoskill_base`: generated skill package with validation-aware candidate selection and semantic hints

## What The Repo Does

Given a set of MCP tool definitions, the pipeline:

1. parses each tool into a normalized `ToolIR`
2. builds raw, schema-only, retrieval, and full-method comparison conditions
3. builds retrieval-based comparison baselines
4. validates generated packages against the schema
5. writes packaged artifacts to `outputs/`
6. evaluates tool-call predictions on benchmark-style tasks
7. evaluates hidden-tool routing where the tool identity is not given to the baseline
8. writes summary tables and experiment reports

## Current Status

What is implemented now:

- deterministic MCP parsing and normalization
- schema validation and package writing
- `raw_mcp`, `schema_only`, `retrieved_docs`, `retrieved_candidates`, `retrieved_memory`, and `autoskill_base`
- validation-aware method-side candidate scoring / reranking for `autoskill_base`
- semantic-hint generation for paraphrase-aware tool use
- benchmark ingestion for simplified and BFCL-style JSON/JSONL
- full integration with BFCL v3 benchmark suites (Full, Subset 100/50/30)
- Unified Routing benchmark for multi-domain routing evaluation
- split-aware benchmark evaluation with pairwise baseline comparisons
- runtime retrieval for docs, candidate tools, and memory examples during benchmark inference
- end-to-end retrieval-augmented generation (RAG) with local and API-based models
- hidden-tool routing evaluation with tool-selection accuracy and joint route-plus-arguments metrics
- error taxonomy and method-win analysis for benchmark failures
- conversion utilities for BFCL-style answer files and MCP tool exports
- three backend modes:
  - `heuristic`
  - `openai_compatible`
  - `local_hf` (direct transformers/torch integration)

What is not implemented yet:

- automated quality scorer / reranker for generated skill packages
- large real harvested MCP dataset pipeline (in progress)
- large real harvested MCP dataset pipeline
- meaningful paper-quality model results

## Main Folders

- [autoskill](autoskill): core package
- [scripts](scripts): runnable CLIs
- [data/raw](data/raw): MCP tool inputs
- [data/eval](data/eval): benchmark inputs
- [configs](configs): experiment configs
- [docs](docs): setup notes
- [tests](tests): regression tests

## Default Data

Default experiment inputs:

- tools: [public_mcp_filesystem_subset.json](data/raw/public_mcp_filesystem_subset.json)
- benchmark: [public_mcp_filesystem_benchmark.jsonl](data/eval/public_mcp_filesystem_benchmark.jsonl)

Additional fixtures:

- [sample_tools.json](data/raw/sample_tools.json)
- [sample_mcp_export.json](data/raw/sample_mcp_export.json)
- [sample_bfcl_style.json](data/eval/sample_bfcl_style.json)
- [sample_bfcl_style.jsonl](data/eval/sample_bfcl_style.jsonl)
- [sample_bfcl_raw_possible_answer.jsonl](data/eval/sample_bfcl_raw_possible_answer.jsonl)

Downloaded external corpora currently present on disk:

- [data/external/bfcl](data/external/bfcl)
- [data/external/modelcontextprotocol-servers](data/external/modelcontextprotocol-servers)

Status note:

- those external corpora are present locally, but the default experiment still uses the curated filesystem subset until we finish fuller ingestion for the downloaded corpora
- external experiment artifacts are now generated under `data/raw/harvested_mcp_reference_servers.json`, `data/raw/bfcl_huggingface_tools.json`, and `data/eval/bfcl_huggingface_*_routing.jsonl`

## Core Commands

Run the packaging pipeline:

```powershell
python scripts\run_pipeline.py
```

Run a benchmark evaluation:

```powershell
python scripts\run_benchmark_eval.py
```

Run hidden-tool routing evaluation:

```powershell
python scripts\run_routing_eval.py
```

Run the full package + benchmark experiment:

```powershell
python scripts\run_experiment.py
```

Run tests:

```powershell
python -m unittest discover -s tests -v
```

## Data Conversion Utilities

Convert BFCL-style input into the repo benchmark format:

```powershell
python scripts\convert_bfcl_to_benchmark.py --in data\eval\sample_bfcl_raw_possible_answer.jsonl --out outputs\converted_benchmark.jsonl
```

Normalize exported MCP tools:

```powershell
python scripts\import_mcp_tools.py --in data\raw\sample_mcp_export.json --out outputs\imported_tools.json
```

## Backend Modes

### 1. `heuristic`

No external model needed. This is the safest way to test the full pipeline structure.

### 2. `openai_compatible`

Uses any endpoint that supports an OpenAI-style `/v1/chat/completions` API.

Sample config:

- [experiment.openai_compatible.sample.json](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\configs\experiment.openai_compatible.sample.json)

### 3. `local_hf`

Loads a local Hugging Face model directly through `transformers` and `torch`, without an HTTP server.

Sample config:

- [experiment.local_hf.sample.json](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\configs\experiment.local_hf.sample.json)

Local setup notes:

- [LOCAL_MODELS.md](docs/LOCAL_MODELS.md)

Local dependency helper:

- [requirements-local.txt](requirements-local.txt)

## Config-Driven Runs

Run a config-backed experiment:

```powershell
python scripts\run_experiment.py --config configs\experiment.local_hf.sample.json
```

Preflight a config without running it:

```powershell
python scripts\run_experiment.py --config configs\experiment.local_hf.qwen25_3b.sample.json --preflight
```

Run a sweep across multiple configs:

```powershell
python scripts\run_experiment_sweep.py configs\experiment.heuristic.sample.json configs\experiment.local_hf.qwen25_3b.sample.json --out outputs\experiment_sweep
```

Preflight a sweep without running experiments:

```powershell
python scripts\run_experiment_sweep.py configs\experiment.heuristic.sample.json configs\experiment.openai_compatible.sample.json --out outputs\experiment_sweep_preflight --preflight-only
```

Current config files:

- [experiment.heuristic.sample.json](configs/experiment.heuristic.sample.json)
- [experiment.openai_compatible.sample.json](configs/experiment.openai_compatible.sample.json)
- [experiment.local_hf.sample.json](configs/experiment.local_hf.sample.json)
- [experiment.local_hf.qwen25_3b.sample.json](configs/experiment.local_hf.qwen25_3b.sample.json)
- [experiment.local_hf.qwen25_7b.sample.json](configs/experiment.local_hf.qwen25_7b.sample.json)
- [experiment.local_hf.qwen25_14b_4bit.sample.json](configs/experiment.local_hf.qwen25_14b_4bit.sample.json)
- [experiment.local_hf.qwen25_32b_4bit.sample.json](configs/experiment.local_hf.qwen25_32b_4bit.sample.json)
- [experiment.bfcl_v3.local_hf.json](configs/experiment.bfcl_v3.local_hf.json)
- [experiment.bfcl_v3_subset50.local_hf.json](configs/experiment.bfcl_v3_subset50.local_hf.json)
- [experiment.bfcl_v3_subset30.local_hf.json](configs/experiment.bfcl_v3_subset30.local_hf.json)
- [experiment.unified_full.local_hf.json](configs/experiment.unified_full.local_hf.json)
- [experiment.openai_compatible.qwen25_14b.sample.json](configs/experiment.openai_compatible.qwen25_14b.sample.json)
- [experiment.openai_compatible.qwen25_32b.sample.json](configs/experiment.openai_compatible.qwen25_32b.sample.json)
- [experiment.harvested_mcp.heuristic.sample.json](configs/experiment.harvested_mcp.heuristic.sample.json)
- [experiment.harvested_mcp.qwen25_14b_4bit.sample.json](configs/experiment.harvested_mcp.qwen25_14b_4bit.sample.json)
- [experiment.bfcl_huggingface_routing.heuristic.sample.json](configs/experiment.bfcl_huggingface_routing.heuristic.sample.json)
- [experiment.bfcl_huggingface_routing.qwen25_32b_endpoint.sample.json](configs/experiment.bfcl_huggingface_routing.qwen25_32b_endpoint.sample.json)

Dataset/model inventory:

- [DATASETS_AND_MODELS.md](docs/DATASETS_AND_MODELS.md)

## Outputs

The main outputs are written under [outputs](outputs).

The most important experiment artifacts are:

- packaged skills under `outputs/<tool_name>/<condition>/`
- benchmark predictions under `outputs/experiment/benchmark/`
- hidden-tool routing records under `outputs/experiment/routing_benchmark/`
- package logs in `outputs/experiment/packages/generation_records.jsonl`
- prediction logs in `outputs/experiment/benchmark/prediction_records.jsonl`
- report tables in `outputs/experiment/reports/`
- experiment metadata in `outputs/experiment/experiment_manifest.json`
- split summaries in `outputs/experiment/benchmark/benchmark_summary_by_split.json`
- routing summaries in `outputs/experiment/routing_benchmark/routing_summary.json`
- pairwise comparisons in `outputs/experiment/benchmark/pairwise_comparisons.json`
- error taxonomy in `outputs/experiment/benchmark/error_taxonomy.json`
- method-win analysis in `outputs/experiment/benchmark/method_win_analysis.json`
- sweep summaries in `outputs/experiment_sweep*/sweep_summary.md`

## Benchmark Results

### BFCL v3 Subset 50 (Qwen-2.5-14B-Instruct)

Results below are generated using a 50-task subset of the Berkeley Function Calling Leaderboard (BFCL) v3, with a Qwen-2.5-14B-Instruct model (4-bit quantization) as both the generator and predictor.

| Method | Exact Match (EM) | Tool Selection Accuracy | Joint EM (Routing) |
| :--- | :---: | :---: | :---: |
| `raw_mcp` | 0.3200 | 0.5800 | 0.4000 |
| `schema_only` | 0.3000 | 0.6000 | 0.3400 |
| `retrieved_docs` | 0.2800 | 0.4400 | 0.2600 |
| `retrieved_candidates` | 0.3000 | 0.6600 | 0.3800 |
| `retrieved_memory` | 0.2800 | 0.0400 | 0.0200 |
| **`autoskill_base`** | **0.3800** | **0.6800** | **0.4200** |

### Retrieval Diagnostics

The benchmark reports also expose retrieval diagnostics for retrieval-driven baselines:

- `tool_retrieval_hit_rate`
- `avg_target_tool_rank`

### Related-work baseline notes

- [RELATED_WORK_BASELINES.md](docs/RELATED_WORK_BASELINES.md)

## Important Caveat

While the repo now includes real model results for BFCL v3, the **default** `python scripts\run_experiment.py` (without arguments) still uses the heuristic backend and the curated filesystem subset. To reproduce the results above, use the specialized configs:

```powershell
python scripts\run_experiment.py --config configs\experiment.bfcl_v3_subset50.local_hf.json
```
