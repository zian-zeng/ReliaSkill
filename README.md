# AutoSkill

AutoSkill is a Stage A prototype for converting raw MCP tool definitions into agent-ready skill packages and comparing them against simple baselines.

The current comparison ladder is:

- `raw_mcp`: raw schema and docs only
- `schema_only`: deterministic cleaned schema package
- `autoskill_base`: generated skill package with validation-aware candidate selection and semantic hints

## What The Repo Does

Given a set of MCP tool definitions, the pipeline:

1. parses each tool into a normalized `ToolIR`
2. builds the three comparison conditions
3. validates generated packages against the schema
4. writes packaged artifacts to `outputs/`
5. evaluates tool-call predictions on benchmark-style tasks
6. writes summary tables and experiment reports

## Current Status

What is implemented now:

- deterministic MCP parsing and normalization
- schema validation and package writing
- `raw_mcp`, `schema_only`, and `autoskill_base`
- validation-aware method-side candidate scoring / reranking for `autoskill_base`
- semantic-hint generation for paraphrase-aware tool use
- benchmark ingestion for simplified and BFCL-style JSON/JSONL
- split-aware benchmark evaluation with pairwise baseline comparisons
- error taxonomy and method-win analysis for benchmark failures
- conversion utilities for BFCL-style answer files and MCP tool exports
- three backend modes:
  - `heuristic`
  - `openai_compatible`
  - `local_hf`

What is not implemented yet:

- retrieval-augmented generation
- quality scorer / reranker
- large real harvested MCP dataset pipeline
- meaningful paper-quality model results

## Main Folders

- [autoskill](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\autoskill): core package
- [scripts](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\scripts): runnable CLIs
- [data/raw](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\data\raw): MCP tool inputs
- [data/eval](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\data\eval): benchmark inputs
- [configs](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\configs): experiment configs
- [docs](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\docs): setup notes
- [tests](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\tests): regression tests

## Default Data

Default experiment inputs:

- tools: [public_mcp_filesystem_subset.json](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\data\raw\public_mcp_filesystem_subset.json)
- benchmark: [public_mcp_filesystem_benchmark.jsonl](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\data\eval\public_mcp_filesystem_benchmark.jsonl)

Additional fixtures:

- [sample_tools.json](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\data\raw\sample_tools.json)
- [sample_mcp_export.json](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\data\raw\sample_mcp_export.json)
- [sample_bfcl_style.json](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\data\eval\sample_bfcl_style.json)
- [sample_bfcl_style.jsonl](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\data\eval\sample_bfcl_style.jsonl)
- [sample_bfcl_raw_possible_answer.jsonl](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\data\eval\sample_bfcl_raw_possible_answer.jsonl)

## Core Commands

Run the packaging pipeline:

```powershell
python scripts\run_pipeline.py
```

Run a benchmark evaluation:

```powershell
python scripts\run_benchmark_eval.py
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

- [LOCAL_MODELS.md](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\docs\LOCAL_MODELS.md)

Local dependency helper:

- [requirements-local.txt](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\requirements-local.txt)

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

- [experiment.heuristic.sample.json](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\configs\experiment.heuristic.sample.json)
- [experiment.openai_compatible.sample.json](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\configs\experiment.openai_compatible.sample.json)
- [experiment.local_hf.sample.json](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\configs\experiment.local_hf.sample.json)
- [experiment.local_hf.qwen25_3b.sample.json](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\configs\experiment.local_hf.qwen25_3b.sample.json)
- [experiment.local_hf.qwen25_7b.sample.json](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\configs\experiment.local_hf.qwen25_7b.sample.json)

## Outputs

The main outputs are written under [outputs](c:\Users\zianz\OneDrive\Documents\GitHub\AutoSkill\outputs).

The most important experiment artifacts are:

- packaged skills under `outputs/<tool_name>/<condition>/`
- benchmark predictions under `outputs/experiment/benchmark/`
- package logs in `outputs/experiment/packages/generation_records.jsonl`
- prediction logs in `outputs/experiment/benchmark/prediction_records.jsonl`
- report tables in `outputs/experiment/reports/`
- experiment metadata in `outputs/experiment/experiment_manifest.json`
- split summaries in `outputs/experiment/benchmark/benchmark_summary_by_split.json`
- pairwise comparisons in `outputs/experiment/benchmark/pairwise_comparisons.json`
- error taxonomy in `outputs/experiment/benchmark/error_taxonomy.json`
- method-win analysis in `outputs/experiment/benchmark/method_win_analysis.json`
- sweep summaries in `outputs/experiment_sweep*/sweep_summary.md`

Current heuristic default experiment signal:

- `raw_mcp`: exact match `0.6667`
- `schema_only`: exact match `0.6667`
- `autoskill_base`: exact match `1.0000`

## Important Caveat

The current repo is structurally ready for real experiments, but the default run still uses heuristic generation and heuristic prediction unless you explicitly switch to a model-backed config.

That means the pipeline is real, but the current default scores are not yet paper-quality model results.
