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
- large-scale dataset construction from local MCP fixtures, locally available public MCP schemas, converted external benchmark tools, and explicitly marked synthetic MCP-like tools
- domain and source tagging across filesystem, search/retrieval, database/sql, calendar/time, git/version-control, issue-tracking, messaging/email mock, web/fetch mock, cloud/storage mock, math/data processing, memory/notes, and system/admin mock
- schema-complexity features for arguments, required/optional fields, enums, nested objects, arrays, boolean flags, side effects, authentication, documentation length, and ambiguity heuristics
- difficulty-tiered positive and adjacent negative controls for easy, medium, and hard examples
- BFCL/API-style, API-Bank-style, and ToolBench-style conversion modules that preserve original signatures, source metadata, normalized schemas, and gold calls when available
- hard distractor inventory construction for hidden-tool routing with lexical similarity, argument overlap, same-domain distractors, side-effect overlap, and adversarial near-miss tools
- multi-candidate skill generation with validation-aware and dev-behavior-aware candidate selection
- compactness-controlled skill variants from ultra-compact through verbose/raw-docs conditions
- prompt-template ablations for compact, boundary-first, schema-minimal, example-rich, safety-aware, and verbose-docs generation
- deterministic repair strategy interface with no-repair, full-regeneration, targeted-section, boundary-only, example-only, argument-template, and taxonomy-conditioned repair variants
- diagnostic stress-test generation for corrupted, over-broad, misleading, malformed, and unsafe skills
- low-compute model configs and a one-GPU scheduler for grouped, resumable dry-run planning under an RTX 5070 Ti-style budget
- sandbox live-execution subset for filesystem, SQLite, and git-like mock tools
- human-written skill upper-bound workflow with balanced sampling, authoring packets, and validation without exposing evaluation labels
- slice-analysis and scientific-comparison extraction for future saved logs
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
- runtime retrieval for docs, candidate tools, and memory examples during benchmark evaluation
- end-to-end retrieval-augmented generation (RAG) with local and API-based models
- hidden-tool routing evaluation with tool-selection accuracy and joint route-plus-arguments metrics
- error taxonomy and method-win analysis for benchmark failures
- conversion utilities for BFCL-style answer files and MCP tool exports
- three backend modes:
  - `heuristic`
  - `openai_compatible`
  - `local_hf` (direct transformers/torch integration)

What still requires future experiment execution:

- learned/calibrated reliability classifier or AUROC reporting
- final GPU multi-model result logs for the revised low-compute reliability framing
- manually authored human skills written by real annotators
- final result tables populated from the selected full experiment run

## Implementation Update Summary

The current implementation branch expands ReliaSkill from a small filesystem-oriented prototype into a low-compute benchmark and experiment harness. These are the fifteen major updates now represented in code, configs, generated preparation artifacts, and analysis scripts:

1. **Large-scale dataset expansion.** `autoskill/tool_collection.py` now supports multiple source categories, deterministic source balancing, deduplication by normalized tool name plus schema hash, schema-complexity features, side-effect labels, difficulty tiers, and source/domain stats. The large-scale config is [large_scale.yaml](configs/data/large_scale.yaml), with an API-Bank-style local fixture at [apibank_style_tools.json](data/raw/apibank_style_tools.json). The latest local build produced 295 tools, 10 sources, 14 domains, 63 side-effect tools, 261 hard tools, and 48 synthetic tools, for a 16.27 percent synthetic fraction.

2. **External benchmark conversion.** `reliaskill/converters/` and [convert_external_benchmarks.py](scripts/convert_external_benchmarks.py) convert BFCL/API-style, API-Bank-style, and ToolBench-style formats into MCP-like raw schemas, ToolIR records, and positive controls when gold calls exist. The current local conversion produced 1,089 unique converted tools and 18,702 positive examples: 995 BFCL tools with 17,003 examples and 94 ToolBench/MCPToolBench++ tools with 1,699 examples. API-Bank is missing locally and is logged as a warning without failing.

3. **Difficulty-tiered controls.** `autoskill/control_generation.py` now generates `positive_easy`, `positive_medium`, `positive_hard`, `negative_easy`, `negative_medium`, and `negative_hard` controls with labels for difficulty, family, negative category, expected failure mode, alternatives, gold tool, gold args, trigger decision, and rationale. The large-scale config is [large_scale.yaml](configs/controls/large_scale.yaml). The latest local build produced 2,950 controls over 295 tools, split into 1,475 dev and 1,475 test examples, with five positive and five negative controls per tool.

4. **Hard distractor routing inventories.** [distractors.py](reliaskill/distractors.py), [build_distractor_inventories.py](scripts/build_distractor_inventories.py), and [distractor_inventory.yaml](configs/routing/distractor_inventory.yaml) build routing examples with easy, medium, hard, and adversarial distractors. The current local inventory contains 5,900 routing examples with 8.0 average candidates: 1,475 examples per distractor level, average name similarity 0.196, and average argument overlap 0.1393.

5. **Multi-candidate skill generation.** `autoskill/multi_candidate.py`, [run_generation.py](scripts/run_generation.py), and [multi_candidate.yaml](configs/skills/multi_candidate.yaml) support K-candidate generation, candidate diversity strategies, validation/dev-behavior/reliability selection policies, and logging of candidate artifacts, scores, selected candidates, and selection reports. The new conditions are wired into [reviewer_baselines.yaml](configs/conditions/reviewer_baselines.yaml), with compatibility shims under `reliaskill/`.

6. **Repair strategy extension.** `autoskill/repair.py` now exposes a strategy interface with `no_repair`, `full_regeneration`, `targeted_section_patch`, `nonuse_boundary_patch`, `example_repair`, `argument_template_repair`, and `failure_taxonomy_repair`. Repair reports include original and repaired hashes, failure type, modified sections, patch text, before/after validation, before/after dev behavior when available, repair round, success flag, and trace records. Ablation configs are wired through `autoskill/ablation.py`, [ablations.yaml](configs/experiments/ablations.yaml), [reviewer_baselines.yaml](configs/conditions/reviewer_baselines.yaml), and [repair_strategies.yaml](configs/repair/repair_strategies.yaml).

7. **Compactness variants and token logging.** `autoskill/compactness.py` and `autoskill/token_accounting.py` add `skill_ultra_compact`, `skill_compact`, `skill_medium`, `skill_verbose`, `generated_docs_verbose`, and `raw_docs_full`. Token accounting uses an available tokenizer when possible and otherwise records a regex approximation. [compactness_variants.yaml](configs/skills/compactness_variants.yaml) logs skill tokens, prompt tokens, total representation tokens, included sections, examples count, and non-use boundary count to [skill_compactness_stats.csv](outputs/tables/skill_compactness_stats.csv).

8. **One-GPU low-compute planning.** [scheduler.py](reliaskill/scheduler.py) and [plan_experiment_run.py](scripts/plan_experiment_run.py) dry-run grouped, resumable one-GPU experiments with model grouping, tool sharding, remaining-call counts, token/runtime estimates, disk estimates, and OOM guards. Model configs live under [configs/models](configs/models). The large-scale dry run reports 2 models, 9 conditions, 290 tools, 1,475 tasks, 26,550 remaining model calls, and about 29 estimated hours under a 12 GB budget, with the 7B config forced to batch size 1.

9. **Live/sandbox execution subset.** `reliaskill/live_exec/` and the live execution scripts build and evaluate safe filesystem, SQLite, and mock-git tasks. The generated subset has 75 tasks across easy/medium/hard levels, read-only and safe-write workflows, invalid query handling, path traversal blocking, and blocked git network operations. Evaluation uses a fresh temporary sandbox per task and records before/after state snapshots.

10. **Saved-log slice analysis.** [slices.py](reliaskill/analysis/slices.py) and [analyze_result_slices.py](scripts/analyze_result_slices.py) join saved logs with tool, control, routing, and compactness metadata; compute metrics by slice; suppress low-n slices; and report condition comparisons. The script writes domain, difficulty, negative-category, distractor-level, tool-complexity, and summary outputs from saved logs only.

11. **Human-written skill workflow.** [human_skill_condition.py](reliaskill/human_skill_condition.py), [sample_human_skill_subset.py](scripts/sample_human_skill_subset.py), [build_human_skill_packets.py](scripts/build_human_skill_packets.py), and [validate_human_skills.py](scripts/validate_human_skills.py) create a real human-upper-bound workflow without fake skills. The current preparation generated a 25-tool balanced subset, authoring packets, `data/human_skills/skills/README.md`, subset stats, validation CSV, protocol report, and validation report.

12. **Prompt-template generation and ablations.** `autoskill/prompt_templates.py`, [prompt_templates.yaml](configs/skills/prompt_templates.yaml), and `scripts/run_generation.py --prompt-templates` support seven templates: `compact_default`, `boundary_first`, `schema_faithful_minimal`, `example_rich`, `safety_side_effect_aware`, `negative_control_aware_dev_only`, and `verbose_docs_style`. Generated artifacts preserve raw generation text and parse errors instead of silently accepting malformed structure. Prompt-template conditions are registered for compact, boundary-first, example-rich, safety-aware, and verbose-docs comparisons.

13. **Diagnostic corrupted-skill stress suite.** [corrupt_skills.py](reliaskill/stress_tests/corrupt_skills.py), [build_skill_stress_tests.py](scripts/build_skill_stress_tests.py), and [stress_tests.yaml](configs/conditions/stress_tests.yaml) generate diagnostic variants for invented arguments, missing required arguments, invalid enums, malformed JSON examples, over-broad use boundaries, missing non-use boundaries, wrong tool boundaries, unsafe destructive instructions, contradictory instructions, bloated irrelevant docs, and misleading examples. The generated detection table logs structural validity, behavior harm rate, safety preservation, reliability decision, gating rejection, and expected-detector success.

14. **Minimum, strong, and stretch experiment plans.** [minimum_credible.yaml](configs/experiments/minimum_credible.yaml), [strong.yaml](configs/experiments/strong.yaml), and [stretch.yaml](configs/experiments/stretch.yaml) define one-GPU run choices. Current dry-run estimates are: minimum, 100 tools, 505 tasks, 7 conditions, 2 models, 7,070 calls, about 7.7 hours; strong, 250 tools, 1,260 tasks, 28 conditions, 2 models, 70,560 calls, about 77 hours; stretch, 290 available tools, 1,475 tasks, 29 conditions, 3 models, 128,325 calls, about 113 hours, with a warning that the configured 320-tool target needs more data.

15. **Scientific comparison extraction.** [comparisons.py](reliaskill/analysis/comparisons.py) and [extract_scientific_comparisons.py](scripts/extract_scientific_comparisons.py) read saved result tables only, evaluate comparison templates, compute metric deltas, conservative CI deltas, paired-test metadata when available, denominators, warnings, claim-support categories, and safe wording suggestions. Current smoke extraction correctly marks all 11 comparisons as `insufficient_data` because future conditions such as `naive_skill`, `repaired_skill`, and `gated_skill` are not yet populated in real result tables.

## Main Folders

- [reliaskill](reliaskill): reliability-centered ToolIR, skill generation, validation, repair, routing, live execution, and analysis modules
- [autoskill](autoskill): historical package kept for compatibility with earlier scripts and baselines
- [scripts](scripts): runnable CLIs
- [data/raw](data/raw): MCP tool inputs
- [data/raw_mcp](data/raw_mcp): large-scale raw MCP-like tool records
- [data/processed_toolir](data/processed_toolir): normalized ToolIR records
- [data/controls](data/controls): difficulty-tiered positive and adjacent negative controls
- [data/routing](data/routing): hidden-tool routing examples with distractor inventories
- [data/live_exec](data/live_exec): safe sandbox execution tasks
- [data/converted_external](data/converted_external): converted BFCL/API-Bank/ToolBench-style records when local inputs exist
- [data/human_skills](data/human_skills): human-skill authoring packets and future submitted skills
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

Build the large local tool-schema dataset:

```powershell
python scripts\collect_mcp_tools.py --config configs\data\minimum.yaml
```

Build the large-scale dataset target:

```powershell
python scripts\collect_mcp_tools.py --config configs\data\large_scale.yaml
```

This collector only reads local files and does not execute external MCP tools or require paid APIs. The default minimum config combines existing MCP fixtures, harvested reference-server schemas already stored on disk, MCPToolBench++ conversions, and BFCL-style converted schemas. Synthetic mock tools are supported by the collector only when a source is explicitly configured as `synthetic_mock`; the default config does not include synthetic tools.

Generated artifacts:

- [tools.jsonl](data/raw_mcp/tools.jsonl): normalized raw MCP/tool definitions with source/domain metadata
- [tools.jsonl](data/processed_toolir/tools.jsonl): parsed ToolIR records
- [dataset_stats.csv](outputs/tables/dataset_stats.csv): source/domain/side-effect statistics
- [domain_complexity_stats.csv](outputs/tables/domain_complexity_stats.csv): domain-level schema complexity and side-effect coverage
- [tool_difficulty_stats.csv](outputs/tables/tool_difficulty_stats.csv): easy/medium/hard difficulty distribution
- [dataset_card.md](outputs/reports/dataset_card.md): reproducibility and coverage summary

Regenerate only the dataset table and card from an existing raw JSONL:

```powershell
python scripts\make_dataset_table.py
```

Each raw record is validated to include `name`, `description`, `inputSchema`, and `source_metadata`. Metadata includes `server`, `domain`, `side_effect_type`, `auth_required`, `args_count`, `required_args_count`, and `enum_count`. Records are deduplicated by source server, tool name, and schema hash with deterministic ordering and seed 42.

Convert locally available external benchmark schemas into MCP-like records:

```powershell
python scripts\convert_external_benchmarks.py --input data\external --output data\converted_external --sources bfcl api_bank toolbench
```

The converter is partial-availability friendly: missing source folders produce warnings, not failures, unless strict mode is enabled. Converted records are marked as converted benchmark tools, not real MCP tools, and preserve `original_benchmark_id`, `original_tool_name`, `original_function_signature`, normalized schema, natural-language request, gold tool call, and split suggestion when present.

Build reproducible positive and adjacent negative controls from the processed ToolIR dataset:

```powershell
python scripts\build_controls.py --config configs\controls\minimum.yaml
```

This writes [dev.jsonl](data/controls/dev.jsonl), [test.jsonl](data/controls/test.jsonl), and [control_stats.csv](outputs/tables/control_stats.csv). Each control includes `category`, `gold_tool`, `gold_args`, `should_trigger`, `split`, and `rationale`, while preserving the existing behavior-evaluation fields such as `tool_name`, `expected_arguments`, and `negative_target`.

Build large-scale controls with explicit difficulty tiers:

```powershell
python scripts\build_controls.py --config configs\controls\large_scale.yaml
```

This writes [dev.jsonl](data/controls/dev.jsonl), [test.jsonl](data/controls/test.jsonl), [control_difficulty_stats.csv](outputs/tables/control_difficulty_stats.csv), and [negative_category_stats.csv](outputs/tables/negative_category_stats.csv). Each control includes `control_id`, `difficulty`, `control_family`, `negative_category`, `expected_failure_mode`, `should_trigger`, `gold_tool`, `gold_args`, `alternative_valid_tools`, and `rationale`.

Build hidden-tool routing examples with hard distractors:

```powershell
python scripts\build_distractor_inventories.py --tools data\processed_toolir\tools.jsonl --controls data\controls\test.jsonl --output data\routing\test_routing.jsonl
```

The routing builder creates candidate sets at configurable sizes with easy, medium, hard, and adversarial distractor levels. It uses same-domain matches, similar names/descriptions, overlapping argument names, side-effect overlap, and confusing opposite actions such as read/write, search/fetch, and create/update. It writes [distractor_stats.csv](outputs/tables/distractor_stats.csv).

Build safe sandbox live-execution tasks:

```powershell
python scripts\build_live_exec_tasks.py --output data\live_exec\live_tasks.jsonl
```

The live subset covers filesystem, SQLite, and git-like mock domains using temporary directories and databases. It is intended for later execution with:

```powershell
python scripts\run_live_exec_eval.py --tasks data\live_exec\live_tasks.jsonl --predictions outputs\future_run\live_predictions.jsonl --output outputs\tables\live_exec_results.csv
```

The live evaluator reports `predicted_call_valid`, `execution_success`, `observation_match`, `state_match`, `unsafe_action_blocked`, and `live_joint_success`.

Build human-skill authoring packets for a real upper-bound baseline:

```powershell
python scripts\sample_human_skill_subset.py --tools data\processed_toolir\tools.jsonl --controls data\controls\dev.jsonl
python scripts\build_human_skill_packets.py
python scripts\validate_human_skills.py
```

Authoring packets expose raw schema, ToolIR, sparse docs, allowed skill format, token budget, formatting examples, and safety notes. They do not expose dev/test controls or gold outputs. Human-authored skills should later be placed under `data/human_skills/skills/` as `SKILL.md` plus `metadata.json`.

Build diagnostic corrupted-skill stress tests:

```powershell
python scripts\build_skill_stress_tests.py
```

Stress variants are marked diagnostic/adversarial and are not mixed into normal conditions unless explicitly configured. They cover invented arguments, missing required arguments, invalid enum values, malformed JSON examples, over-broad use boundaries, unsafe destructive guidance, contradictory instructions, bloated irrelevant docs, and misleading examples.

Recompute utility, harm, confidence intervals, and paired significance tests from saved prediction JSONL:

```powershell
python scripts\make_tables.py --input outputs\sample_run
```

The table builder reads saved `prediction_records.jsonl`, `routing_records.jsonl`, and `reliability_records.jsonl` files under the input run directory. It writes [main_results.csv](outputs/tables/main_results.csv), [harm_utility.csv](outputs/tables/harm_utility.csv), and [stat_tests.csv](outputs/tables/stat_tests.csv) without rerunning generation or evaluation.

Generate all result tables directly from saved logs:

```powershell
python scripts\make_tables.py --run outputs\final_run
```

This writes CSV and LaTeX `.tex` files under `outputs/final_run/tables/` for dataset/tool statistics, main results, utility/harm, ablations, model scaling, error analysis, reliability threshold sensitivity, and cost/latency. The LaTeX files are generated from the same logged CSV/JSONL artifacts and include a provenance comment.

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

Generate skills with prompt-template, compactness, and multi-candidate support:

```powershell
python scripts\run_generation.py --config configs\skills\multi_candidate.yaml
```

Generation supports `K=1` for baseline compatibility and `K=3` by default for multi-candidate selection. Candidate strategies include `concise_default`, `boundary_heavy`, `example_heavy`, `safety_first`, and `minimal_token`. Prompt templates are config-driven through [prompt_templates.yaml](configs/skills/prompt_templates.yaml), and compactness variants are configured in [compactness_variants.yaml](configs/skills/compactness_variants.yaml). Candidate artifacts are written under `skills/<tool_id>/candidates/` or `generated_skills/<template_id>/<tool_id>.json` depending on the entry point, with `candidate_scores.jsonl`, `selected_candidate.json`, and `selection_report.json` available for analysis.

Plan a one-GPU experiment without launching model execution:

```powershell
python scripts\plan_experiment_run.py --config configs\experiments\strong.yaml --gpu_budget_gb 12
```

The scheduler groups work by model, runs all selected conditions before unloading that model, supports sharding by `tool_id`, resumes from existing prediction files, estimates examples, model calls, token volume, runtime, and disk usage, and raises warnings when prompt length, batch size, or estimated VRAM exceed the requested budget. Dry-run outputs are [run_plan.md](outputs/reports/run_plan.md) and [run_plan.csv](outputs/tables/run_plan.csv).

Analyze future saved logs by reviewer-facing slices:

```powershell
python scripts\analyze_result_slices.py --run outputs\future_run --tools data\processed_toolir\tools.jsonl --controls data\controls\test.jsonl --routing data\routing\test_routing.jsonl
```

Slice analysis breaks metrics down by domain, source type, difficulty, complexity tier, required-argument bucket, enum/nested-object presence, side-effect type, negative category, distractor level, candidate set size, and skill token bucket. It writes domain, difficulty, negative-category, distractor-level, and tool-complexity CSVs plus [slice_analysis_summary.md](outputs/reports/slice_analysis_summary.md).

Extract scientific comparison summaries from future saved tables:

```powershell
python scripts\extract_scientific_comparisons.py --tables-dir outputs\tables
```

This reads actual result tables only and writes [scientific_comparison_summary.json](outputs/reports/scientific_comparison_summary.json), [scientific_comparison_summary.md](outputs/reports/scientific_comparison_summary.md), and [key_comparisons.csv](outputs/tables/key_comparisons.csv). It compares `naive_skill` versus `raw_mcp`, repair versus naive skill, gating versus repair, compact versus verbose skills, multi-candidate versus single-candidate skills, targeted repair versus full regeneration, 3B gated versus 7B raw schema, and hard/negative/side-effect/high-distractor slices. Missing data is reported as `insufficient_data`; the script does not fabricate significance or claims.

Every experiment run also writes audit artifacts:

- `manifest.json`: run id, git commit hash, config hash, seed, model names, quantization settings, hardware, config, and output paths
- `audit_records.jsonl`: prompt template, raw prompt, raw model output, parsed prediction, validation report, behavior report, repair report, reliability score, and artifact pointer per generation/prediction/reliability event

The regular saved `prediction_records.jsonl`, `routing_records.jsonl`, and `reliability_records.jsonl` remain sufficient for table regeneration without rerunning generation or evaluation; the audit JSONL adds the raw provenance needed to inspect any row.

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
- [FULL_EXPERIMENT_RUN.md](docs/FULL_EXPERIMENT_RUN.md)

Experiment scale configs:

- [minimum_credible.yaml](configs/experiments/minimum_credible.yaml): 100 tools, 8+ domains, 3 positives and 3 negatives per tool, 4-tool routing, 3B/7B models, core condition ladder
- [strong.yaml](configs/experiments/strong.yaml): 200-300 tools, 10+ domains, 5 positives and 5 negatives per tool, 8/16-tool routing, full condition ladder, multi-candidate K=3, compactness variants, repair comparisons, live execution subset
- [stretch.yaml](configs/experiments/stretch.yaml): 300+ tools, 12+ domains, expanded converted external examples, multi-candidate K=5, 8/16/32-tool routing, optional third model and human-skill condition

Low-compute model configs:

- [qwen2_5_3b_instruct_4bit.yaml](configs/models/qwen2_5_3b_instruct_4bit.yaml)
- [qwen2_5_7b_instruct_4bit.yaml](configs/models/qwen2_5_7b_instruct_4bit.yaml)
- [optional_small_model.yaml](configs/models/optional_small_model.yaml)
- [optional_cpu_or_mock_smoke.yaml](configs/models/optional_cpu_or_mock_smoke.yaml)

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

## Full Experiment Runbook

For the complete low-compute workflow, including dataset construction, external conversion, controls, hard distractors, live execution, human-skill packets, skill generation, repair strategies, scheduler planning, table export, slice analysis, scientific comparisons, and safe claim wording, see:

- [ReliaSkill Full Experiment Runbook](docs/FULL_EXPERIMENT_RUN.md)
