# ReliaSkill

ReliaSkill is a reliability-centered MCP skill cold-start research harness. It converts raw MCP schemas and sparse documentation into compact skill artifacts, validates them deterministically, tests them against positive and negative controls, repairs targeted failures, scores pre-deployment reliability, and gates artifacts before downstream agent exposure.

The project is intentionally focused: it is not a generic agent platform, a trajectory-pool distillation system, or a multi-file skill ecosystem. The target contribution is **reliable MCP schema/doc -> compact skill construction under cold-start constraints, with validation, repair, scoring, and deploy/reject gating**.

The current reliability ladder is:

- `raw_mcp`: raw schema and docs only
- `schema_only`: deterministic cleaned schema package
- `docs_only`: sparse documentation-only control
- `naive_skill`: one-shot compact generated skill
- `validated_skill`: generated skill plus deterministic structural validation
- `repaired_skill`: validated skill after targeted section-level repair
- `gated_skill`: repaired skill with reliability score and deploy/repair/reject decision

Historical baselines remain available for comparison:

- `retrieved_docs`: retrieved documentation snippets
- `retrieved_candidates`: candidate-tool retrieval baseline
- `retrieved_memory`: skill-memory retrieval baseline
- `autoskill_base`: legacy validation-aware generated skill package

## What The Repo Does

Given a set of MCP tool definitions, the pipeline:

1. parses each tool into a normalized `ToolIR` with doc-completeness, schema-complexity, ambiguity, provenance, and side-effect hints
2. builds raw/schema/docs/naive/validated/repaired/gated skill conditions
3. validates templates, examples, enums, required fields, unsupported arguments, contradictory guidance, non-use boundaries, and compactness
4. runs behavior-grounded tests over positive controls and adjacent negative controls
5. applies conservative targeted repair to failing sections
6. scores likely reliability and gates deploy/repair/reject decisions
7. writes standardized packages and experiment reports
8. preserves the legacy benchmark and routing evaluators for comparison against earlier drafts

## Current Status

What is implemented now:

- deterministic MCP parsing and normalization
- ToolIR reliability features for doc completeness, schema complexity, ambiguity, provenance, side effects, and safety hints
- schema validation and package writing
- structured validation reports with section, repairability, and evidence fields
- behavior-grounded positive/negative-control harness
- targeted repair for schema-inconsistent templates/examples and behavior failures from negative controls
- rule-based reliability scoring and deploy/repair/reject gating
- standardized reliability packaging with validation, behavior, repair, and score artifacts
- `raw_mcp`, `schema_only`, `retrieved_docs`, `retrieved_candidates`, `retrieved_memory`, and `autoskill_base`
- `docs_only`, `naive_skill`, `validated_skill`, `repaired_skill`, and `gated_skill`
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

- full harvested-MCP dataset pipeline beyond the current converted MCPToolBench++ slice
- learned/calibrated reliability classifier or AUROC reporting
- paper-quality GPU multi-model results for the revised low-compute reliability framing

## Main Folders

- [autoskill](autoskill): core Python package; kept under the historical import name for compatibility
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
- [data/external/mcptoolbenchpp](data/external/mcptoolbenchpp)

Status note:

- those external corpora are present locally, but the default experiment still uses the curated filesystem subset for fast smoke tests
- external experiment artifacts are now generated under `data/raw/harvested_mcp_reference_servers.json`, `data/raw/bfcl_huggingface_tools.json`, and `data/eval/bfcl_huggingface_*_routing.jsonl`
- the larger reliability fixture is available as `data/raw/mcptoolbenchpp_tools.json` and `data/eval/mcptoolbenchpp_reliability.jsonl`

## Core Commands

Run the packaging pipeline:

```powershell
python scripts\run_pipeline.py
```

Run the revised reliability pipeline:

```powershell
python scripts\run_reliability_pipeline.py --config configs\experiment.reliability.heuristic.sample.json
```

This writes packages under `outputs/reliability_heuristic_sample/packages/<tool>/<condition>/` with:

- `SKILL.md`
- `schema.normalized.json`
- `examples.jsonl`
- `validation_report.json`
- `behavior_report.json`
- `repair_report.json`
- `reliability_score.json`
- `metadata.json`

It also writes run-level artifacts:

- `outputs/reliability_heuristic_sample/reliability_manifest.json`
- `outputs/reliability_heuristic_sample/reliability_summary.json`
- `outputs/reliability_heuristic_sample/reliability_records.jsonl`
- `outputs/reliability_heuristic_sample/reports/reliability_report.md`
- `outputs/reliability_heuristic_sample/reports/reliability_summary.csv`

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

## Dataset Construction And Statistics

Build the paper-scale local tool-schema dataset:

```powershell
python scripts\collect_mcp_tools.py --config configs\data\minimum.yaml
```

This collector only reads local files and does not execute external MCP tools or require paid APIs. The default minimum config combines existing MCP fixtures, harvested reference-server schemas already stored on disk, MCPToolBench++ conversions, and BFCL-style converted schemas. Synthetic mock tools are supported by the collector only when a source is explicitly configured as `synthetic_mock`; the default config does not include synthetic tools.

Generated artifacts:

- [tools.jsonl](data/raw_mcp/tools.jsonl): normalized raw MCP/tool definitions with source/domain metadata
- [tools.jsonl](data/processed_toolir/tools.jsonl): parsed ToolIR records
- [dataset_stats.csv](outputs/tables/dataset_stats.csv): source/domain/side-effect statistics
- [dataset_card.md](outputs/reports/dataset_card.md): reproducibility and coverage summary

Regenerate only the dataset table and card from an existing raw JSONL:

```powershell
python scripts\make_dataset_table.py
```

Each raw record is validated to include `name`, `description`, `inputSchema`, and `source_metadata`. Metadata includes `server`, `domain`, `side_effect_type`, `auth_required`, `args_count`, `required_args_count`, and `enum_count`. Records are deduplicated by source server, tool name, and schema hash with deterministic ordering and seed 42.

Build reproducible positive and adjacent negative controls from the processed ToolIR dataset:

```powershell
python scripts\build_controls.py --config configs\controls\minimum.yaml
```

This writes [dev.jsonl](data/controls/dev.jsonl), [test.jsonl](data/controls/test.jsonl), and [control_stats.csv](outputs/tables/control_stats.csv). Each control includes `category`, `gold_tool`, `gold_args`, `should_trigger`, `split`, and `rationale`, while preserving the existing behavior-evaluation fields such as `tool_name`, `expected_arguments`, and `negative_target`.

Recompute utility, harm, confidence intervals, and paired significance tests from saved prediction JSONL:

```powershell
python scripts\make_tables.py --input outputs\sample_run
```

The table builder reads saved `prediction_records.jsonl`, `routing_records.jsonl`, and `reliability_records.jsonl` files under the input run directory. It writes [main_results.csv](outputs/tables/main_results.csv), [harm_utility.csv](outputs/tables/harm_utility.csv), and [stat_tests.csv](outputs/tables/stat_tests.csv) without rerunning inference.

Generate all paper tables directly from saved logs:

```powershell
python scripts\make_tables.py --run outputs\final_run
```

This writes CSV and Overleaf-ready `.tex` files under `outputs/final_run/tables/` for dataset/tool statistics, main results, utility/harm, ablations, model scaling, error analysis, reliability threshold sensitivity, and cost/latency. The LaTeX files are generated from the same logged CSV/JSONL artifacts and include a provenance comment so table numbers are not edited by hand.

Generate reliability score audit artifacts:

```powershell
python scripts\run_reliability_sensitivity.py
```

ReliaSkill scores use `R = 100*(0.20*V + 0.30*P + 0.30*N + 0.10*A + 0.05*C + 0.05*S) - 5*repair_rounds`, with `deploy >= 85`, `repair` from `60` to `85`, and `reject < 60` or any non-repairable critical failure. The script writes [reliability_threshold_sensitivity.csv](outputs/tables/reliability_threshold_sensitivity.csv), `outputs/tables/reliability_weight_sensitivity.csv`, [reliability_calibration.pdf](outputs/figures/reliability_calibration.pdf), and [reliability_score_definition.md](outputs/reports/reliability_score_definition.md).

Run the reviewer-baseline smoke experiment:

```powershell
python scripts\run_experiment.py --config configs\experiments\baselines_smoke.yaml
```

This adds `prompt_only_careful_tool_use`, `raw_schema_plus_examples`, `generated_docs_no_validation`, `generic_validator_no_behavior_tests`, `full_regeneration_repair`, `human_written_skill_upper_bound`, `retrieval_tool_card`, `larger_model_naive_skill`, and `adversarial_distractor_inventory` as named conditions. Prompt slots for every tool/condition are logged under [outputs/prompts](outputs/prompts), and the comparable baseline table is written to [baseline_results.csv](outputs/tables/baseline_results.csv). A full-minimum config is available at [baselines_minimum.yaml](configs/experiments/baselines_minimum.yaml).

Run the final component ablation table:

```powershell
python scripts\run_ablation_table.py --config configs\experiments\ablations.yaml
```

This writes [ablation_results.csv](outputs/tables/ablation_results.csv) with `full ReliaSkill`, validation/behavior/control/repair/gating/boundary/example/compactness ablations, full-regeneration repair, and a dev/test leakage check. The table reports joint EM, argument validity, trigger precision, harmful skill injection rate, reliability score, and deterministic confidence intervals. Per-tool details are written to `outputs/ablations/ablation_details.jsonl`.

Extract qualitative cases without cherry-picking:

```powershell
python scripts\extract_qualitative_cases.py
```

The extractor uses deterministic rules for representative examples: category-first selection, highest-confidence failures where multiple candidates exist, and the first held-out failure for the final ReliaSkill case. It writes [qualitative_cases.md](outputs/reports/qualitative_cases.md) and [error_analysis.csv](outputs/tables/error_analysis.csv) with tool names, user requests, predictions, gold labels, failure types, repair diffs, and source artifact paths.

Every experiment run also writes audit artifacts:

- `manifest.json`: run id, git commit hash, config hash, seed, model names, quantization settings, hardware, config, and output paths
- `audit_records.jsonl`: prompt template, raw prompt, raw model output, parsed prediction, validation report, behavior report, repair report, reliability score, and artifact pointer per generation/prediction/reliability event

The regular saved `prediction_records.jsonl`, `routing_records.jsonl`, and `reliability_records.jsonl` remain sufficient for table regeneration without rerunning inference; the audit JSONL adds the raw provenance needed to inspect any row.

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
- [experiment.reliability.heuristic.sample.json](configs/experiment.reliability.heuristic.sample.json)
- [model_comparison.low_compute.sample.json](configs/model_comparison.low_compute.sample.json)
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
- [MCP_COLD_START_RELIABILITY.md](docs/MCP_COLD_START_RELIABILITY.md)
- [LARGER_MCP_NEGATIVE_CONTROL_BENCHMARK.md](docs/LARGER_MCP_NEGATIVE_CONTROL_BENCHMARK.md)
- [LOW_COMPUTE_EXPERIMENTS.md](docs/LOW_COMPUTE_EXPERIMENTS.md)

Run the low-compute model comparison preflight:

```powershell
python scripts\run_model_comparison.py --config configs\model_comparison.low_compute.sample.json --preflight-only
```

Download and convert MCPToolBench++ when network access is available:

```powershell
python scripts\download_mcptoolbenchpp.py --out data\external\mcptoolbenchpp
python scripts\convert_mcptoolbenchpp.py --input data\external\mcptoolbenchpp --category file_system --category search --category browser --limit 300
```

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
