# ReliaSkill Full Experiment Runbook

> Maintainer note: this is an archival run-planning note from an earlier experiment buildout. It is retained for reproducibility context, but the README is the canonical public summary of the reported evaluation.

This runbook describes the intended full evaluation path for ReliaSkill after the code and data-preparation updates. It is written for a single-machine, single-GPU workflow, with an RTX 5070 Ti-style 12 GB VRAM budget as the reference constraint.

The goal is to produce reproducible evidence from saved logs, prediction records, and deterministic analysis scripts.

## Core Principle

ReliaSkill should be evaluated as a reliability method, not only as a prompt style. The experiment should show:

- whether compact generated skills improve tool use over raw schemas
- whether validation, repair, and gating reduce harm on negative controls
- whether improvements survive hard, ambiguous, adjacent, and distractor-heavy cases
- whether a low-compute 3B model with reliable skills can approach or exceed a 7B model using raw schemas
- whether compact skills are better than verbose generated documentation under a fixed context budget
- whether targeted repair is better than full regeneration or simple boundary patching
- whether results hold across domains, source types, schema complexity, and side-effect tools
- whether live execution outcomes improve, not only JSON prediction metrics

Do not use test controls for skill selection, repair, threshold tuning, or task revision. Test logs are for final reporting only.

## Current Prepared State

The current local preparation artifacts establish the following starting point for full experiment runs:

- dataset build: 290 tools, 10 sources, 14 domains, 63 side-effect tools, 261 hard tools, and 48 synthetic tools
- synthetic fraction: 16.27 percent, with synthetic tools explicitly marked
- external conversion: 1,089 unique converted tools and 18,702 positive examples
- BFCL conversion subset: 995 tools and 17,003 examples
- ToolBench/MCPToolBench++ conversion subset: 94 tools and 1,699 examples
- API-Bank local availability: missing locally, warning logged without failing conversion
- selected controls: 2,900 total controls over 290 tools
- selected control split: 1,450 dev and 1,450 test
- per-tool controls: 5 positive and 5 negative controls
- selected routing inventory: 5,800 routing examples
- selected routing distractor levels: 1,450 easy, 1,450 medium, 1,450 hard, and 1,450 adversarial
- routing candidate set: 8.0 average candidates
- routing similarity diagnostics: 0.196 average name similarity and 0.1393 average argument overlap
- live execution subset: 75 safe sandbox tasks across filesystem, SQLite, and mock-git domains
- human-skill workflow: 25 balanced authoring packets prepared, with no fake completed human skills
- current scientific comparison extraction: all 11 comparison templates correctly return `insufficient_data` until future experiment result tables contain the required conditions

These numbers are preparation outputs, not final model-result claims. They can be used to describe benchmark coverage, task construction, and feasibility, but final performance claims must wait for saved prediction logs and generated result tables.

## Experiment Scales

Use one of the three planned configs depending on available time.

### Minimum Credible Run

Config:

```powershell
configs\experiments\minimum_credible.yaml
```

Purpose:

- enough to avoid the "toy filesystem benchmark" criticism
- 100 tools
- at least 8 domains
- 3 positive and 3 negative controls per tool
- routing with 4 candidate tools
- 3B and 7B 4-bit models
- core conditions only

Recommended when:

- time is short
- the GPU is shared
- the first complete result table pass is needed quickly

Plan command:

```powershell
python scripts\plan_experiment_run.py --config configs\experiments\minimum_credible.yaml --gpu_budget_gb 12
```

Current dry-run estimate on the local prepared dataset:

- 100 tools
- 505 tasks
- 7 conditions
- 2 models
- 7,070 model calls
- about 7.7 estimated hours

### Strong Run

Config:

```powershell
configs\experiments\strong.yaml
```

Purpose:

- main reviewer-facing run
- 200 to 300 tools
- at least 10 domains
- 5 positive and 5 negative controls per tool
- routing with 8 and 16 candidates
- 3B and 7B 4-bit models
- full condition ladder
- multi-candidate generation with K=3
- compactness variants
- repair strategy comparisons
- sandbox live-execution subset

Plan command:

```powershell
python scripts\plan_experiment_run.py --config configs\experiments\strong.yaml --gpu_budget_gb 12
```

This is the recommended default full run.

Current dry-run estimate on the local prepared dataset:

- 250 tools
- 1,260 tasks
- 28 conditions
- 2 models
- 70,560 model calls
- about 77 estimated hours

### Stretch Run

Config:

```powershell
configs\experiments\stretch.yaml
```

Purpose:

- 300+ tools
- at least 12 domains
- expanded external converted examples
- multi-candidate generation with K=5
- routing with 8, 16, and 32 candidate tools
- optional third model
- human-written skill condition if real skills are available

Plan command:

```powershell
python scripts\plan_experiment_run.py --config configs\experiments\stretch.yaml --gpu_budget_gb 12
```

Use this only after the strong run is stable.

Current dry-run estimate on the local prepared dataset:

- 290 available tools
- 1,450 selected tasks
- 29 conditions
- 3 models
- 128,325 model calls
- about 113 estimated hours
- warning: the configured 320-tool target needs more data

## Step 0: Sanity Checks

From the repo root:

```powershell
python -m unittest discover -s tests -v
```

Expected:

- tests pass before any result-generating run
- failures are fixed before running GPU jobs
- generated result tables are not edited manually

Useful quick checks:

```powershell
python scripts\plan_experiment_run.py --config configs\experiments\strong.yaml --gpu_budget_gb 12
python scripts\extract_scientific_comparisons.py --tables-dir outputs\tables
```

The comparison extractor may report `insufficient_data` before real experiments are complete. That is correct.

## Step 1: Build External Benchmark Conversions

Convert whatever external data is already available locally:

```powershell
python scripts\convert_external_benchmarks.py --input data\external --output data\converted_external --sources bfcl api_bank toolbench
```

Expected outputs:

- `data/converted_external/conversion_records.jsonl`
- `data/converted_external/raw_tools.jsonl`
- `data/converted_external/toolir.jsonl`
- `data/converted_external/positive_controls.jsonl`
- `data/converted_external/bfcl_records.jsonl`
- `data/converted_external/api_bank_records.jsonl`
- `data/converted_external/toolbench_records.jsonl`
- `outputs/tables/external_conversion_stats.csv`
- `outputs/reports/external_conversion_report.md`

Current local conversion result:

- 1,089 unique converted tools
- 18,702 positive examples
- BFCL: 995 tools and 17,003 examples
- ToolBench/MCPToolBench++: 94 tools and 1,699 examples
- API-Bank: missing locally, logged as a warning without failing

Quality checks:

- missing sources should be warnings, not failures, unless strict mode is enabled
- converted benchmark tools must be marked as converted, not real MCP tools
- gold tool calls must be preserved only when present
- no gold labels should be fabricated

Report language after this step:

- "We convert locally available external function-calling schemas into a common MCP-like schema representation."
- "Converted tools retain benchmark provenance and are separated from real or synthetic MCP-like tools."
- "Gold calls are used only when provided by the source benchmark."

## Step 2: Build The Large-Scale Tool Dataset

Build the main dataset:

```powershell
python scripts\collect_mcp_tools.py --config configs\data\large_scale.yaml
```

Expected outputs:

- `data/raw_mcp/tools.jsonl`
- `data/processed_toolir/tools.jsonl`
- `outputs/tables/dataset_stats.csv`
- `outputs/tables/domain_complexity_stats.csv`
- `outputs/tables/tool_difficulty_stats.csv`
- `outputs/reports/dataset_card.md`

Current local dataset build:

- 290 tools
- 10 sources
- 14 domains
- 63 side-effect tools
- 261 hard tools
- 48 synthetic tools
- 16.27 percent synthetic fraction

Dataset requirements for the strong run:

- 200 to 300 tools
- at least 10 domains
- synthetic fraction preferably below 25 to 30 percent
- source types are explicitly marked
- duplicates removed by normalized tool name and schema hash
- deterministic seed 42

Minimum acceptance thresholds:

- at least 100 tools
- at least 8 domains
- non-trivial side-effect tools
- non-trivial hard tools

Reviewer-facing coverage claims should be based on `dataset_stats.csv`, `domain_complexity_stats.csv`, and `tool_difficulty_stats.csv`.

Safe phrases:

- "The benchmark covers X tools across Y domains."
- "Synthetic tools are explicitly marked and account for Z percent of the dataset."
- "The dataset includes schema complexity factors such as nested objects, enums, optional fields, side effects, and authentication flags."
- "We deduplicate tools by normalized name and schema hash."

Avoid:

- "representative of MCP-like tools beyond the evaluated setup"
- "comprehensive"
- "real-world" for synthetic or converted records

## Step 3: Build Difficulty-Tiered Controls

Build controls:

```powershell
python scripts\build_controls.py --config configs\controls\large_scale.yaml
```

Expected outputs:

- `data/controls/dev.jsonl`
- `data/controls/test.jsonl`
- `outputs/tables/control_difficulty_stats.csv`
- `outputs/tables/negative_category_stats.csv`

Current local control build:

- 290 selected tools
- 2,900 selected controls
- 1,450 selected dev controls
- 1,450 selected test controls
- 5 positive and 5 negative controls per tool
- medium and hard negative categories rotate across adjacent intent, explanation-vs-action, known-path/no-search, read-vs-search, near-miss, destructive/read-only, similar-tool distractor, missing-required-info, and ambiguous-abstain cases

Strong-run target:

- 1 easy positive per tool
- 2 medium positives per tool
- 2 hard positives per tool
- 1 easy negative per tool
- 2 medium negatives per tool
- 2 hard negatives per tool

Control labels:

- `control_id`
- `difficulty`
- `control_family`
- `negative_category`
- `expected_failure_mode`
- `should_trigger`
- `gold_tool`
- `gold_args`
- `alternative_valid_tools`
- `rationale`

Quality checks:

- dev/test split is deterministic
- exact duplicate requests are removed across splits
- test controls are not used for selection, repair, or threshold tuning
- negative controls include adjacent and near-miss cases, not only unrelated requests

Safe phrases:

- "We evaluate both tool-triggering utility and abstention behavior."
- "Hard controls include indirect requests, adjacent tools, distractors, nested or enum arguments, and missing optional information."
- "Negative controls test over-triggering, destructive/read-only mismatches, explanation-versus-action mismatches, and missing required information."

## Step 4: Build Hard Distractor Routing Inventories

Build routing examples:

```powershell
python scripts\build_distractor_inventories.py --tools data\processed_toolir\tools.jsonl --controls data\controls\test.jsonl --output data\routing\test_routing.jsonl
```

Expected outputs:

- `data/routing/test_routing.jsonl`
- `outputs/tables/distractor_stats.csv`

Current local routing inventory:

- 5,900 routing examples
- 8.0 average candidates
- 1,450 selected easy examples
- 1,450 selected medium examples
- 1,450 selected hard examples
- 1,450 selected adversarial examples
- 0.196 average name similarity
- 0.1393 average argument overlap

Routing fields:

- `target_tool_id`
- `user_request`
- `candidate_tool_ids`
- `correct_tool_id`
- `distractor_level`
- `distractor_generation_reason`
- `should_trigger`

Distractor levels:

- `easy`: random tools from different domains
- `medium`: same domain but different intent
- `hard`: similar name, description, or arguments
- `adversarial`: intentionally near-miss tool

Quality checks:

- correct tool position is randomized
- correct tool is not always in the same slot
- candidate sizes match the experiment config
- hard/adversarial examples have measurable name similarity or argument overlap

Safe phrases:

- "Routing examples include hard distractors selected by lexical similarity, argument overlap, domain match, and side-effect similarity."
- "This tests whether skills help when the correct tool is not obvious."

## Step 5: Build Live Execution Tasks

Build sandbox tasks:

```powershell
python scripts\build_live_exec_tasks.py --output data\live_exec\live_tasks.jsonl
```

Expected outputs:

- `data/live_exec/live_tasks.jsonl`
- `outputs/tables/live_exec_task_stats.csv`

Current local live subset:

- 75 tasks
- filesystem, SQLite, and mock-git domains
- easy, medium, and hard coverage
- read-only tasks and safe write tasks
- invalid SQL handling
- path traversal blocking
- blocked git network operations

Supported domains:

- filesystem
- SQLite
- git-like mock operations

Later, after predictions exist:

```powershell
python scripts\run_live_exec_eval.py --tasks data\live_exec\live_tasks.jsonl --predictions outputs\strong\live_predictions.jsonl --output outputs\tables\live_exec_results.csv
```

Live metrics:

- `predicted_call_valid`
- `execution_success`
- `observation_match`
- `state_match`
- `unsafe_action_blocked`
- `live_joint_success`

Quality checks:

- tasks use temporary directories or databases
- no network operations
- path traversal is blocked
- before/after state snapshots are saved
- cleanup happens after each task

Safe phrases:

- "A small sandbox subset evaluates whether improved tool calls lead to executable outcomes."
- "Live execution is intentionally limited to safe local domains."

## Step 6: Prepare Human Skill Upper-Bound Packets

Sample a balanced subset:

```powershell
python scripts\sample_human_skill_subset.py --tools data\processed_toolir\tools.jsonl --controls data\controls\dev.jsonl
```

Build authoring packets:

```powershell
python scripts\build_human_skill_packets.py
```

Validate submitted human skills:

```powershell
python scripts\validate_human_skills.py
```

Expected outputs:

- `data/human_skills/authoring_packets/`
- `data/human_skills/skills/`
- `outputs/tables/human_skill_subset_stats.csv`
- `outputs/reports/human_skill_protocol.md`

Current local human-skill preparation:

- 25 balanced tools sampled
- authoring packets generated
- `data/human_skills/skills/README.md` generated
- no fake completed human skills generated
- subset stats, validation CSV, protocol report, and validation report generated

Important:

- do not create fake human skills
- do not expose dev/test controls in packets
- do not expose gold outputs
- authors write `SKILL.md` and `metadata.json`
- validation uses the same structural, compactness, and schema-faithfulness checks

Safe phrases:

- "The human-written condition is an upper-bound workflow, not an automatically generated baseline."
- "Authoring packets exclude evaluation labels and controls."

## Step 7: Generate Skills And Candidate Artifacts

Generate skills:

```powershell
python scripts\run_generation.py --config configs\skills\multi_candidate.yaml
```

Relevant configs:

- `configs/skills/multi_candidate.yaml`
- `configs/skills/compactness_variants.yaml`
- `configs/skills/prompt_templates.yaml`
- `configs/repair/repair_strategies.yaml`
- `configs/conditions/stress_tests.yaml`

Candidate strategies:

- `concise_default`
- `boundary_heavy`
- `example_heavy`
- `safety_first`
- `minimal_token`

Prompt templates:

- `compact_default`
- `boundary_first`
- `schema_faithful_minimal`
- `example_rich`
- `safety_side_effect_aware`
- `negative_control_aware_dev_only`
- `verbose_docs_style`

Compactness variants:

- `ultra_compact`: 100 to 150 tokens
- `compact`: 200 to 300 tokens
- `medium`: 400 to 600 tokens
- `verbose`: 800 to 1200 tokens
- `raw_docs_full`: full docs where available

Candidate outputs:

- `skills/{tool_id}/candidates/*.json`
- `candidate_scores.jsonl`
- `selected_candidate.json`
- `selection_report.json`
- `outputs/tables/skill_compactness_stats.csv`
- `outputs/tables/prompt_template_generation_stats.csv`

Rules:

- use dev controls only for behavior-aware selection
- never use test controls for selection
- do not hide failed candidates
- log all candidates
- use K=3 for the strong run and K=1 for single-candidate baseline compatibility

Safe phrases:

- "ReliaSkill generates multiple candidate skill artifacts and selects by validation and dev-control behavior."
- "All candidates, including failed candidates, are logged for analysis."
- "Test controls are held out from generation, selection, and repair."

## Step 8: Run Repair Strategy Conditions

Repair config:

```powershell
configs\repair\repair_strategies.yaml
```

Repair strategies:

- `no_repair`
- `full_regeneration`
- `targeted_section_patch`
- `nonuse_boundary_patch`
- `example_repair`
- `argument_template_repair`
- `failure_taxonomy_repair`

Failure taxonomy:

- `unsupported_argument`
- `missing_required_field`
- `invalid_enum`
- `malformed_example`
- `over_triggering`
- `under_triggering`
- `contradictory_instruction`
- `unsafe_side_effect_boundary`
- `verbosity_or_context_bloat`

Repair report fields:

- `original_skill_hash`
- `repaired_skill_hash`
- `failure_type`
- `modified_sections`
- `patch_text`
- `validation_before`
- `validation_after`
- `behavior_before_dev`
- `behavior_after_dev`
- `repair_round`
- `repair_success`

Safe phrases:

- "Targeted repair is evaluated against full regeneration and section-specific alternatives."
- "Repair decisions use dev behavior controls and deterministic validation, not test outcomes."

## Step 9: Plan The GPU Run

Always dry-run first:

```powershell
python scripts\plan_experiment_run.py --config configs\experiments\strong.yaml --gpu_budget_gb 12
```

Expected outputs:

- `outputs/reports/run_plan.md`
- `outputs/tables/run_plan.csv`

Current `configs/experiments/large_scale.yaml` dry-run estimate:

- 2 models
- 9 conditions
- 290 tools
- 1,450 selected tasks
- 26,550 remaining model calls
- about 29 estimated hours
- Qwen 3B and 7B 4-bit configs fit under a 12 GB budget
- 7B is guarded with `batch_size: 1`

Plan should include:

- number of tools
- number of examples
- number of models
- number of conditions
- number of model calls
- estimated token volume
- estimated runtime
- estimated disk usage
- model grouping order
- warnings about infeasible settings

Feasibility checks:

- 7B runs should default to small batch size, usually 1
- prompt length must respect `max_prompt_tokens`
- estimated VRAM must stay within budget
- model paths must be local or configurable
- scheduler should group all conditions for one model before unloading

Safe phrases:

- "The run plan estimates calls, tokens, runtime, and disk usage before model execution."
- "The scheduler is designed to avoid repeated model loading and to resume from existing predictions."

## Step 10: Run The Selected Experiment

When ready, use the selected experiment config with the existing runner entry point used by the project:

```powershell
python scripts\run_experiment.py --config configs\experiments\strong.yaml
```

Expected logs should include:

- prediction records
- routing records
- reliability records
- generation records
- audit records
- manifests
- condition metadata
- model metadata

Do not interrupt a run without preserving partial outputs. Resume support should be used instead of deleting partial predictions.

## Step 11: Regenerate Tables From Saved Logs

After predictions exist:

```powershell
python scripts\make_tables.py --run outputs\strong
```

Expected core outputs:

- `outputs/tables/main_results.csv`
- `outputs/tables/harm_utility.csv`
- `outputs/tables/stat_tests.csv`
- `outputs/tables/baseline_results.csv`
- `outputs/tables/ablation_results.csv`
- `outputs/tables/reliability_threshold_sensitivity.csv`
- `outputs/tables/reliability_weight_sensitivity.csv`
- `outputs/tables/error_analysis.csv`
- `outputs/tables/live_exec_results.csv`
- `outputs/tables/skill_compactness_stats.csv`
- `outputs/tables/prompt_template_generation_stats.csv`
- `outputs/tables/stress_test_inventory.csv`
- `outputs/tables/stress_test_detection_results.csv`

Metrics to report:

- joint exact match
- tool accuracy
- argument validity
- trigger precision
- trigger recall
- harmful skill injection rate
- skill-induced harm rate
- reliability score
- deploy/repair/reject rate
- mean prompt tokens
- mean latency
- live joint success
- unsafe action blocked
- routing joint route-plus-arguments success

Rules:

- regenerate tables from logs
- do not manually edit result cells
- keep denominators visible
- mark slices below minimum sample size

## Step 12: Run Slice Analysis

Analyze saved logs:

```powershell
python scripts\analyze_result_slices.py --run outputs\strong --tools data\processed_toolir\tools.jsonl --controls data\controls\test.jsonl --routing data\routing\test_routing.jsonl
```

Expected outputs:

- `outputs/tables/slice_analysis_by_domain.csv`
- `outputs/tables/slice_analysis_by_difficulty.csv`
- `outputs/tables/slice_analysis_by_negative_category.csv`
- `outputs/tables/slice_analysis_by_distractor_level.csv`
- `outputs/tables/slice_analysis_by_tool_complexity.csv`
- `outputs/reports/slice_analysis_summary.md`

Slice dimensions:

- domain
- source type
- difficulty
- tool complexity tier
- required argument bucket
- enum presence
- nested-object presence
- side-effect type
- negative category
- distractor level
- candidate set size
- skill token bucket

Safe phrases:

- "Gains are largest on [slice] when denominator and confidence intervals support it."
- "The method weakens on [slice], suggesting a boundary for the current approach."
- "For small slices, we report descriptive trends but avoid strong claims."

## Step 13: Extract Scientific Comparisons

Generate claim summaries:

```powershell
python scripts\extract_scientific_comparisons.py --tables-dir outputs\tables
```

Expected outputs:

- `outputs/reports/scientific_comparison_summary.json`
- `outputs/reports/scientific_comparison_summary.md`
- `outputs/tables/key_comparisons.csv`

Current local extraction status:

- all 11 comparison templates run
- all 11 are marked `insufficient_data`
- this is expected because future result tables do not yet contain conditions such as `naive_skill`, `repaired_skill`, and `gated_skill`
- no performance claim should be made from the current smoke tables

Comparison templates:

- `naive_skill_vs_raw_mcp`
- `repaired_vs_naive`
- `gated_vs_repaired`
- `compact_vs_verbose`
- `multi_candidate_vs_single_candidate`
- `targeted_repair_vs_full_regeneration`
- `three_b_gated_vs_seven_b_raw`
- `hard_cases_only`
- `negative_controls_only`
- `side_effect_tools_only`
- `high_distractor_routing_only`

Claim support categories:

- `supported`
- `weakly_supported`
- `mixed`
- `unsupported`
- `insufficient_data`

Safe wording:

- strong support: "improves"
- weak support: "suggests"
- mixed support: "improves on X but not Y"
- unsupported: "does not support"
- insufficient data: "we do not draw a claim"

Important:

- do not fabricate statistical significance
- do not state a claim when the category is `insufficient_data`
- include denominators
- include warnings when sample size is too small

## Step 14: Run Diagnostic Stress Tests

Build stress inventory:

```powershell
python scripts\build_skill_stress_tests.py
```

Expected outputs:

- `data/stress_skills/`
- `outputs/tables/stress_test_inventory.csv`

After evaluation, expected output:

- `outputs/tables/stress_test_detection_results.csv`

Current local stress-test preparation:

- diagnostic artifacts generated under `data/stress_skills/`
- inventory generated at `outputs/tables/stress_test_inventory.csv`
- detection table generated at `outputs/tables/stress_test_detection_results.csv`
- detection fields include structural validity, behavior harm rate, safety preservation, reliability decision, gating rejection, and expected-detector success

Stress conditions:

- `corrupted_skill_invented_arg`
- `corrupted_skill_overbroad`
- `corrupted_skill_unsafe_side_effect`
- `corrupted_skill_malformed_example`
- `corrupted_skill_mixed`

Use stress tests as diagnostics only. Do not mix corrupted skills into main benchmark conditions unless the config explicitly asks for diagnostic stress-test evaluation.

Safe phrases:

- "Stress tests are diagnostic and are not included in the main benchmark average."
- "The validator is expected to catch schema errors, behavior tests are expected to catch over-triggering, and gating is expected to reject high-risk artifacts."

## Step 15: Export The Evidence Bundle

The final evidence bundle should contain:

Dataset and task construction:

- `data/raw_mcp/tools.jsonl`
- `data/processed_toolir/tools.jsonl`
- `data/controls/dev.jsonl`
- `data/controls/test.jsonl`
- `data/routing/test_routing.jsonl`
- `data/live_exec/live_tasks.jsonl`
- `outputs/reports/dataset_card.md`
- `outputs/reports/external_conversion_report.md`
- `outputs/reports/human_skill_protocol.md`

Plans and manifests:

- `outputs/reports/run_plan.md`
- `outputs/tables/run_plan.csv`
- experiment `manifest.json`
- `audit_records.jsonl`

Main tables:

- `outputs/tables/dataset_stats.csv`
- `outputs/tables/domain_complexity_stats.csv`
- `outputs/tables/tool_difficulty_stats.csv`
- `outputs/tables/control_difficulty_stats.csv`
- `outputs/tables/negative_category_stats.csv`
- `outputs/tables/distractor_stats.csv`
- `outputs/tables/main_results.csv`
- `outputs/tables/harm_utility.csv`
- `outputs/tables/stat_tests.csv`
- `outputs/tables/ablation_results.csv`
- `outputs/tables/baseline_results.csv`
- `outputs/tables/live_exec_results.csv`
- `outputs/tables/skill_compactness_stats.csv`
- `outputs/tables/prompt_template_generation_stats.csv`
- `outputs/tables/key_comparisons.csv`

Slice tables:

- `outputs/tables/slice_analysis_by_domain.csv`
- `outputs/tables/slice_analysis_by_difficulty.csv`
- `outputs/tables/slice_analysis_by_negative_category.csv`
- `outputs/tables/slice_analysis_by_distractor_level.csv`
- `outputs/tables/slice_analysis_by_tool_complexity.csv`

Reports:

- `outputs/reports/slice_analysis_summary.md`
- `outputs/reports/scientific_comparison_summary.md`
- `outputs/reports/scientific_comparison_summary.json`
- `outputs/reports/qualitative_cases.md`
- `outputs/reports/reliability_score_definition.md`

## Suggested Result Story, Conditional On Actual Results

Only use these phrases when the generated comparison summary supports them.

Skill generation:

- Supported: "Compact skill artifacts improve joint tool-call accuracy over raw MCP schemas."
- Weak: "The results suggest compact skills help over raw schemas, though gains are modest."
- Mixed: "Skills improve triggering but not argument validity, indicating that schema-faithful argument grounding remains difficult."
- Unsupported: "The current results do not support a general skill-generation benefit over raw schemas."

Repair:

- Supported: "Targeted repair improves reliability over naive generation while preserving compactness."
- Mixed: "Repair reduces schema errors but does not consistently improve downstream task success."
- Unsupported: "Repair does not improve over naive skills in this run."

Gating:

- Supported: "Gating trades a small amount of utility for lower harmful over-triggering."
- Mixed: "Gating reduces harm on negative controls but also suppresses some valid positives."
- Unsupported: "The current gating threshold does not improve the harm-utility tradeoff."

Compactness:

- Supported: "Compact skills outperform verbose generated documentation under the same low-compute setting."
- Mixed: "Verbose documentation helps some easy positives but hurts hard or distractor-heavy routing through context bloat."
- Unsupported: "The compactness comparison does not show a reliable advantage."

Low-compute model comparison:

- Supported: "A 3B model with gated ReliaSkill artifacts closes part of the gap to, or exceeds, a 7B model using raw schemas."
- Mixed: "The 3B gated condition improves abstention and harm metrics but does not match 7B raw-schema utility."
- Unsupported: "The 3B gated condition does not close the gap to 7B raw-schema performance."

Hard cases:

- Supported: "ReliaSkill gains are larger on hard, ambiguous, and high-distractor examples."
- Mixed: "The method helps hard positives but remains brittle on adversarial near-miss negatives."
- Unsupported: "The results do not show larger gains on hard cases."

Live execution:

- Supported: "The live sandbox subset shows that better structured calls translate into improved executable outcomes."
- Mixed: "JSON validity improves, but state-match or observation-match remains the bottleneck."
- Unsupported: "The live subset does not show an execution-level improvement."

## Final Pre-Submission Checklist

Before writing final result claims:

- `python -m unittest discover -s tests -v` passes
- dataset has enough tools and domains for the selected scale
- synthetic fraction is reported and below the selected threshold
- controls have dev/test split and no duplicate requests across splits
- run plan fits the GPU budget
- prediction logs exist for all required model/condition pairs
- missing runs are either completed or explicitly excluded
- tables are regenerated from saved logs
- scientific comparison summary is generated
- unsupported or insufficient comparisons are not promoted into claims
- human-written skills, if used, were actually authored by humans
- diagnostic stress-test results are separated from main benchmark averages
- generated result files are kept separate from source code and configs

## Minimal Command Chain For The Strong Run

```powershell
python -m unittest discover -s tests -v
python scripts\convert_external_benchmarks.py --input data\external --output data\converted_external --sources bfcl api_bank toolbench
python scripts\collect_mcp_tools.py --config configs\data\large_scale.yaml
python scripts\build_controls.py --config configs\controls\large_scale.yaml
python scripts\build_distractor_inventories.py --tools data\processed_toolir\tools.jsonl --controls data\controls\test.jsonl --output data\routing\test_routing.jsonl
python scripts\build_live_exec_tasks.py --output data\live_exec\live_tasks.jsonl
python scripts\plan_experiment_run.py --config configs\experiments\strong.yaml --gpu_budget_gb 12
python scripts\run_generation.py --config configs\skills\multi_candidate.yaml
python scripts\run_experiment.py --config configs\experiments\strong.yaml
python scripts\make_tables.py --run outputs\strong
python scripts\analyze_result_slices.py --run outputs\strong --tools data\processed_toolir\tools.jsonl --controls data\controls\test.jsonl --routing data\routing\test_routing.jsonl
python scripts\extract_scientific_comparisons.py --tables-dir outputs\tables
```

The `run_experiment.py` command is the expensive step. Everything before it is setup, validation, or dry-run planning; everything after it reads saved logs.
