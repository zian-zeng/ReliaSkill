# ReliaSkill

Pre-deployment validation, repair, and gating for reliable MCP-style tool-use skills.

ReliaSkill is a research pipeline for MCP skill cold-start. Raw MCP schemas expose tool interfaces, but they often leave the agent-facing usage policy implicit: when to call the tool, when to abstain, and how to assemble valid arguments from a natural-language request.

ReliaSkill converts raw MCP-like schemas and sparse documentation into compact, schema-faithful skill artifacts before downstream agent exposure. Each artifact can include an explicit purpose summary, use and non-use boundaries, canonical argument templates, schema-grounded examples, validation reports, repair traces, and a deployability decision.

The central claim is that reliable tool use is partly a representation problem. ReliaSkill inserts a governed representation layer between protocol-level tool exposure and LLM tool invocation, and tests that improved invocation does not come at the cost of over-triggering on adjacent negative controls.

ReliaSkill is intentionally scoped. It is not a generic agent framework, an experience-rich skill-learning system, a GUI-agent skill ecosystem, or a trajectory distillation system.

<!-- Poster-derived figure assets are not currently checked in as repo image files. Add exported poster figures here only after committing the actual image files. -->

## Why This Matters

- Raw schemas are too thin: they specify accepted arguments, but not reliable use boundaries.
- Naive skill generation can be fluent but unfaithful: it may invent arguments, omit required fields, or broaden the tool's intended scope.
- Tool onboarding should happen before deployment: generated tool representations should be treated as candidates, not trusted artifacts.
- ReliaSkill validates, behavior-tests, repairs, and gates skill artifacts before they are exposed to downstream tool-using agents.

## Pipeline

| Stage | Description |
| --- | --- |
| 1. ToolIR++ normalization | Parses MCP-like schemas into a normalized intermediate representation that preserves the original schema and adds reliability metadata such as provenance, documentation completeness, schema complexity, ambiguity, side-effect hints, and safety hints. |
| 2. Compact skill generation | Produces a compact artifact with a purpose summary, when-to-use guidance, when-not-to-use guidance, a canonical argument template, and schema-faithful examples. |
| 3. Structural validation | Checks unsupported arguments, missing required fields, enum errors, malformed examples, contradictory guidance, missing non-use boundaries, and compactness constraints. |
| 4. Behavior-grounded evaluation | Tests positive controls and adjacent negative controls so that tool-use gains are evaluated alongside abstention behavior. |
| 5. Targeted repair | Patches localized failing sections, such as examples, argument templates, or non-use boundaries, instead of regenerating the whole skill by default. |
| 6. Deployment gating | Assigns explicit DEPLOY, REPAIR, or REJECT decisions based on validation evidence, behavior evidence, repair traces, and reliability scoring. |

## What Is In This Repository

The current codebase implements:

- MCP/tool schema parsing and normalization.
- ToolIR++ reliability features for schema complexity, documentation quality, ambiguity, provenance, side effects, and safety hints.
- Skill generation and prompt-template variants.
- Deterministic structural validation.
- Behavior-grounded positive and adjacent negative controls.
- Targeted repair strategies and full-regeneration repair baselines.
- Rule-based reliability scoring and deploy/repair/reject gating.
- Hidden-tool routing benchmarks with hard distractor inventories.
- BFCL/API-style conversion utilities.
- MCPToolBench++/ToolBench-style conversion utilities when local data exists.
- A sandbox live-execution subset for filesystem, SQLite, and git-like mock tools.
- Slice analysis and scientific comparison extraction from saved logs.
- Low-compute experiment planning and scheduling.
- `heuristic`, `openai_compatible`, and `local_hf` backend modes.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `reliaskill/` | ReliaSkill-facing modules for ToolIR, validation, repair, routing, live execution, scheduling, converters, and analysis. |
| `autoskill/` | Historical compatibility package and shared implementation used by earlier experiment runners and baselines. |
| `scripts/` | Command-line entry points for data construction, generation, evaluation, routing, analysis, and table export. |
| `configs/` | JSON/YAML configs for backends, experiments, skills, controls, routing, models, repair, and data collection. |
| `data/raw/` | Curated raw tool inputs and benchmark-derived tool files. |
| `data/raw_mcp/` | Large-scale raw MCP-like tool records. |
| `data/processed_toolir/` | Normalized ToolIR records. |
| `data/controls/` | Development and held-out test controls. |
| `data/routing/` | Hidden-tool routing examples with distractor inventories. |
| `data/live_exec/` | Safe sandbox execution tasks. |
| `data/converted_external/` | Converted external benchmark records when local sources are available. |
| `data/human_skills/` | Human-skill authoring packets and submitted human skills. |
| `outputs/` | Generated packages, logs, tables, reports, plans, and experiment artifacts. |
| `docs/` | Additional runbooks and setup notes. |
| `tests/` | Unit and regression tests. |

## Installation

ReliaSkill is a Python project. The code uses modern typing syntax, so Python 3.10 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The base requirements are intentionally small:

- `pyyaml`
- `tqdm`
- `huggingface_hub`

For local Hugging Face inference with `local_hf`, install the optional local-model requirements:

```powershell
python -m pip install -r requirements-local.txt
```

This installs `transformers`, `torch`, `accelerate`, and `sentencepiece`. Quantized loading may require additional hardware-specific packages such as `bitsandbytes`; it is not installed by default.

## Quick Start

The default commands use small local fixtures and the heuristic backend unless a model-backed config is supplied.

Run the packaging pipeline:

```powershell
python scripts\run_pipeline.py
```

Run the reliability pipeline:

```powershell
python scripts\run_reliability_pipeline.py --config configs\experiment.reliability.heuristic.sample.json
```

Run benchmark evaluation:

```powershell
python scripts\run_benchmark_eval.py
```

Run hidden-tool routing evaluation:

```powershell
python scripts\run_routing_eval.py
```

Run tests:

```powershell
python -m unittest discover -s tests -v
```

## Reproducing The Main Experiments

The full experiment path is designed to regenerate evidence from saved logs rather than hand-edited tables. A complete run can be expensive; start with planning and smoke tests before launching model-backed evaluation.

1. Build or collect tool data:

```powershell
python scripts\convert_external_benchmarks.py --input data\external --output data\converted_external --sources bfcl api_bank toolbench
python scripts\collect_mcp_tools.py --config configs\data\large_scale.yaml
```

2. Build controls:

```powershell
python scripts\build_controls.py --config configs\controls\large_scale.yaml
```

3. Build routing distractors:

```powershell
python scripts\build_distractor_inventories.py --tools data\processed_toolir\tools.jsonl --controls data\controls\test.jsonl --output data\routing\test_routing.jsonl
```

4. Generate, validate, and repair skills:

```powershell
python scripts\run_generation.py --config configs\skills\multi_candidate.yaml
python scripts\run_reliability_pipeline.py --config configs\experiment.reliability.heuristic.sample.json
```

5. Plan and run benchmark evaluation:

```powershell
python scripts\plan_experiment_run.py --config configs\experiments\strong.yaml --gpu_budget_gb 12
python scripts\run_experiment.py --config configs\experiments\strong.yaml
```

6. Build tables from saved logs:

```powershell
python scripts\make_tables.py --run outputs\strong
```

7. Run slice analysis and scientific comparison extraction:

```powershell
python scripts\analyze_result_slices.py --run outputs\strong --tools data\processed_toolir\tools.jsonl --controls data\controls\test.jsonl --routing data\routing\test_routing.jsonl
python scripts\extract_scientific_comparisons.py --tables-dir outputs\tables
```

The complete command chain and runbook are in [docs/FULL_EXPERIMENT_RUN.md](docs/FULL_EXPERIMENT_RUN.md).

## Datasets And Controls

The current local prepared state includes:

| Quantity | Value |
| --- | ---: |
| MCP-like tools | 295 |
| Sources | 10 |
| Domains | 14 |
| Side-effect tools | 63 |
| Hard tools | 261 |
| Synthetic tools | 48 |
| Total controls | 2,950 |
| Development controls | 1,475 |
| Held-out test controls | 1,475 |
| Per-tool controls | 5 positive and 5 negative |
| Hidden-tool routing examples | 5,900 |
| Average routing candidates | 8 |
| Routing examples per distractor level | 1,475 |

Controls are split into development and held-out test sets. Development controls may be used for candidate selection, repair, and threshold tuning; test controls are reserved for final reporting.

Converted benchmark schemas and synthetic tools are marked by provenance. They should be described as MCP-like or converted benchmark records, not as production MCP deployments.

## Representation Conditions

The paper reports the main ReliaSkill ladder. The current saved-log experiments also include newer prompt-template and reviewer-baseline condition names. These names should not be collapsed unless the underlying artifact construction is identical.

| Condition | Description |
| --- | --- |
| `raw_mcp` | Raw schema and sparse documentation exposed directly. |
| `schema_only` | Deterministically cleaned schema package. |
| `docs_only` | Sparse documentation-only control. |
| `retrieved_docs` | Runtime retrieved documentation snippets. |
| `retrieved_candidates` | Candidate-tool retrieval baseline for routing. |
| `retrieved_memory` | Skill-memory retrieval baseline. |
| `naive_skill` | One-shot compact generated skill in the paper ladder. |
| `naive_skill_k1` | Single-candidate generated skill in the newer saved-log condition set. |
| `validated_skill` | Generated skill plus deterministic structural validation report. |
| `repaired_skill` | Validated skill after conservative targeted repair. |
| `gated_skill` | Paper-ladder repaired skill with reliability score and deploy/repair/reject decision. |
| `multi_candidate_repaired_gated` | Newer saved-log multi-candidate, repaired, gated condition. It is related to but not identical to the paper's `gated_skill` condition name. |
| `autoskill_base` | Legacy validation-aware generated skill package used for comparison. |
| `raw_schema_plus_examples` | Raw schema augmented with examples. |
| `generated_docs_no_validation` | Generated documentation without the full validation and behavior-test pipeline. |
| `generic_validator_no_behavior_tests` | Structural validator baseline without behavior-grounded tests. |
| `full_regeneration_repair` | Repair by regenerating the whole artifact. |
| `skill_prompt_compact_default` | Compact default prompt-template skill condition. |
| `skill_prompt_boundary_first` | Prompt-template condition that foregrounds use and non-use boundaries. |
| `skill_prompt_example_rich` | Prompt-template condition with more examples. |
| `skill_prompt_safety_aware` | Prompt-template condition emphasizing side effects and safety. |
| `skill_prompt_verbose_docs` | Verbose-docs-style prompt-template condition. |
| `skill_ultra_compact`, `skill_compact`, `skill_medium`, `skill_verbose` | Compactness-controlled skill variants. |
| `raw_docs_full`, `generated_docs_verbose` | Verbose documentation baselines. |
| `human_written_skill_upper_bound` | Human-authored skill workflow when real submitted artifacts are available. |

## Latest Results

### Paper Result: Main ReliaSkill Ladder

The paper's main Qwen2.5-7B result set reports the following ladder:

| Condition | Joint EM | Selection Accuracy | Argument Validity |
| --- | ---: | ---: | ---: |
| `raw_mcp` | 17.15% | 26.07% | 43.66% |
| `schema_only` | 15.73% | 25.80% | 41.22% |
| `naive_skill` | 18.85% | 27.36% | 50.07% |
| `gated_skill` | 21.12% | 31.39% | 52.78% |

Ablation results from the paper:

| System | Joint EM | Argument Validity | Selection Accuracy |
| --- | ---: | ---: | ---: |
| Full ReliaSkill | 21.12% | 52.78% | 31.39% |
| w/o Repair | 20.41% | 53.05% | 27.39% |
| w/o Validation | 18.85% | 50.07% | 27.36% |
| w/o Examples | 15.73% | 41.22% | 25.80% |

Argument Validity is not strictly monotonic: w/o Repair has slightly higher Argument Validity than Full ReliaSkill, but Full ReliaSkill has higher Joint EM and Selection Accuracy.

### Latest Saved-Log Multi-Model Results

The tables below use the latest saved-log condition names and the latest pasted multi-model results. They are not identical to the paper's main ReliaSkill ladder because they include additional prompt-template and baseline conditions.

#### Structured-Call Results

| Model | Condition | Exact Match | Argument Validity |
| --- | --- | ---: | ---: |
| gemma2-2B | `raw_mcp` | 0.4380 | 0.8108 |
| gemma2-2B | `autoskill_base` | 0.4393 | 0.6963 |
| gemma2-2B | `human_written_skill_upper_bound` | 0.3037 | 0.7538 |
| gemma2-2B | `skill_prompt_boundary_first` | 0.5207 | 0.7840 |
| gemma2-2B | `skill_prompt_verbose_docs` | 0.5254 | 0.7985 |
| Qwen2.5-1.5B-Instruct | `raw_mcp` | 0.3858 | 0.7540 |
| Qwen2.5-1.5B-Instruct | `schema_only` | 0.3424 | 0.7301 |
| Qwen2.5-1.5B-Instruct | `retrieved_docs` | 0.4034 | 0.8266 |
| Qwen2.5-1.5B-Instruct | `autoskill_base` | 0.3431 | 0.6736 |
| Qwen2.5-1.5B-Instruct | `full_regeneration_repair` | 0.4380 | 0.6927 |
| Qwen2.5-1.5B-Instruct | `skill_prompt_compact_default` | 0.5851 | 0.7242 |
| Qwen2.5-1.5B-Instruct | `skill_prompt_boundary_first` | 0.6163 | 0.7531 |
| Qwen2.5-1.5B-Instruct | `skill_prompt_example_rich` | 0.5681 | 0.7384 |
| Qwen2.5-1.5B-Instruct | `skill_prompt_safety_aware` | 0.6007 | 0.7363 |
| Qwen2.5-1.5B-Instruct | `skill_prompt_verbose_docs` | 0.5614 | 0.7841 |
| Qwen2.5-7B | `raw_mcp` | 0.5302 | 0.9663 |
| Qwen2.5-7B | `schema_only` | 0.5098 | 0.9526 |
| Qwen2.5-7B | `autoskill_base` | 0.6332 | 0.9066 |
| Qwen2.5-7B | `raw_schema_plus_examples` | 0.5980 | 0.9593 |
| Qwen2.5-7B | `generated_docs_no_validation` | 0.6190 | 0.9260 |
| Qwen2.5-7B | `generic_validator_no_behavior_tests` | 0.6529 | 0.9172 |
| Qwen2.5-7B | `full_regeneration_repair` | 0.6285 | 0.9528 |
| Qwen2.5-7B | `naive_skill_k1` | 0.6244 | 0.8924 |
| Qwen2.5-7B | `multi_candidate_repaired_gated` | 0.6183 | 0.8331 |
| phi 3.5-mini | `raw_mcp` | 0.3397 | 0.9697 |
| phi 3.5-mini | `autoskill_base` | 0.4244 | 0.9602 |
| phi 3.5-mini | `human_written_skill_upper_bound` | 0.3261 | 0.9649 |
| phi 3.5-mini | `skill_prompt_boundary_first` | 0.6373 | 0.9693 |
| phi 3.5-mini | `skill_prompt_verbose_docs` | 0.6217 | 0.9681 |
| llama3.2 1B | `raw_mcp` | 0.3342 | 0.8685 |
| llama3.2 1B | `autoskill_base` | 0.3776 | 0.9224 |
| llama3.2 1B | `human_written_skill_upper_bound` | 0.3871 | 0.9288 |
| llama3.2 1B | `skill_prompt_boundary_first` | 0.5281 | 0.9322 |
| llama3.2 1B | `skill_prompt_verbose_docs` | 0.5220 | 0.9307 |

#### Hidden-Tool Routing Results

| Model | Condition | Tool Accuracy | Joint Exact |
| --- | --- | ---: | ---: |
| gemma2-2B | `raw_mcp` | 0.5214 | 0.2102 |
| gemma2-2B | `autoskill_base` | 0.6278 | 0.2698 |
| gemma2-2B | `human_written_skill_upper_bound` | 0.5241 | 0.1519 |
| gemma2-2B | `skill_prompt_boundary_first` | 0.5647 | 0.3180 |
| gemma2-2B | `skill_prompt_verbose_docs` | 0.6373 | 0.3403 |
| Qwen2.5-1.5B-Instruct | `raw_mcp` | 0.5214 | 0.1444 |
| Qwen2.5-1.5B-Instruct | `schema_only` | 0.5159 | 0.1376 |
| Qwen2.5-1.5B-Instruct | `retrieved_docs` | 0.5498 | 0.1980 |
| Qwen2.5-1.5B-Instruct | `retrieved_candidates` | 0.6359 | 0.2176 |
| Qwen2.5-1.5B-Instruct | `autoskill_base` | 0.6278 | 0.1702 |
| Qwen2.5-1.5B-Instruct | `generated_docs_verbose` | 0.6576 | 0.2725 |
| Qwen2.5-1.5B-Instruct | `raw_docs_full` | 0.5769 | 0.2149 |
| Qwen2.5-1.5B-Instruct | `skill_prompt_compact_default` | 0.5424 | 0.2637 |
| Qwen2.5-1.5B-Instruct | `skill_prompt_boundary_first` | 0.5647 | 0.3153 |
| Qwen2.5-1.5B-Instruct | `skill_prompt_safety_aware` | 0.5580 | 0.3010 |
| Qwen2.5-1.5B-Instruct | `skill_prompt_verbose_docs` | 0.6373 | 0.3302 |
| Qwen2.5-7B | `raw_mcp` | 0.5214 | 0.3431 |
| Qwen2.5-7B | `schema_only` | 0.5159 | 0.3146 |
| Qwen2.5-7B | `autoskill_base` | 0.6278 | 0.4224 |
| Qwen2.5-7B | `raw_schema_plus_examples` | 0.5186 | 0.3756 |
| Qwen2.5-7B | `generated_docs_no_validation` | 0.5458 | 0.3912 |
| Qwen2.5-7B | `generic_validator_no_behavior_tests` | 0.5478 | 0.4081 |
| Qwen2.5-7B | `full_regeneration_repair` | 0.5451 | 0.4088 |
| Qwen2.5-7B | `naive_skill_k1` | 0.5471 | 0.3769 |
| Qwen2.5-7B | `multi_candidate_repaired_gated` | 0.5485 | 0.3580 |
| phi 3.5-mini | `raw_mcp` | 0.5214 | 0.2522 |
| phi 3.5-mini | `autoskill_base` | 0.6278 | 0.3132 |
| phi 3.5-mini | `human_written_skill_upper_bound` | 0.5241 | 0.2373 |
| phi 3.5-mini | `skill_prompt_boundary_first` | 0.5647 | 0.4529 |
| phi 3.5-mini | `skill_prompt_verbose_docs` | 0.6373 | 0.4271 |
| llama3.2 1B | `raw_mcp` | 0.5214 | 0.2224 |
| llama3.2 1B | `autoskill_base` | 0.6278 | 0.2624 |
| llama3.2 1B | `human_written_skill_upper_bound` | 0.5241 | 0.2400 |
| llama3.2 1B | `skill_prompt_boundary_first` | 0.5647 | 0.3776 |
| llama3.2 1B | `skill_prompt_verbose_docs` | 0.6373 | 0.3519 |

Structured-call Exact Match evaluates whether the produced call matches the gold call. Argument Validity checks whether produced arguments are parseable and schema-faithful. Hidden-tool routing Tool Accuracy checks whether the model selects the right tool from candidates. Hidden-tool routing Joint Exact requires both routing and argument correctness. The latest saved-log tables are not identical to the paper's main ReliaSkill ladder because they include additional prompt-template and baseline conditions.

## Key Takeaways From Current Results

- Across several smaller models, `skill_prompt_boundary_first` and `skill_prompt_verbose_docs` often improve structured-call Exact Match over `raw_mcp`.
- In hidden-tool routing, verbose-doc or boundary-first representations often improve Joint Exact over `raw_mcp`.
- On Qwen2.5-7B, `generic_validator_no_behavior_tests` has the highest structured-call Exact Match among the listed saved-log conditions.
- On Qwen2.5-7B routing, `autoskill_base` has the highest hidden-tool routing Joint Exact among the listed routing conditions.
- The latest saved-log table does not support a claim that `multi_candidate_repaired_gated` dominates all baselines. The paper's main ReliaSkill ladder should be reported separately from the newer saved-log multi-model table.

## Reliability And Safety Notes

- Negative-control precision in the paper result should be interpreted as no observed harmful activation on the held-out negative controls, not as a production safety guarantee.
- Structural validation checks skill artifacts. Argument Validity measures model-generated calls.
- Production deployment still needs least-privilege permissions, sandboxing, audit logs, rate limits, monitoring, and human approval for high-impact actions.
- Converted benchmark schemas and synthetic tools should not be overstated as real production MCP deployments.

## Limitations

- ReliaSkill focuses on MCP skill cold-start, not experience-rich skill evolution.
- The corpus combines MCP-like tools, converted benchmark schemas, and explicitly marked synthetic tools.
- Results do not guarantee generalization to all production MCP servers, proprietary models, or live external APIs.
- Current evaluation emphasizes structured-call prediction and adjacent negative-control abstention; live execution and end-to-end task completion need further work.
- The reliability score is rule-based and auditable, not a learned calibrated probability of correctness.

## Additional Documentation

- [Full experiment runbook](docs/FULL_EXPERIMENT_RUN.md)
- [Local model setup](docs/LOCAL_MODELS.md)
- [Dataset and model notes](docs/DATASETS_AND_MODELS.md)
- [MCP cold-start reliability architecture](docs/MCP_COLD_START_RELIABILITY.md)
- [Low-compute experiments](docs/LOW_COMPUTE_EXPERIMENTS.md)
- [Larger MCP negative-control benchmark](docs/LARGER_MCP_NEGATIVE_CONTROL_BENCHMARK.md)
- [Related-work baselines](docs/RELATED_WORK_BASELINES.md)

## Citation

```bibtex
@misc{zeng2026reliaskill,
  title={ReliaSkill: From Raw MCP Schemas to Reliable Skills for Tool-Using LLM Agents},
  author={Zeng, Zian and Yuan, Mu},
  year={2026},
  note={Manuscript}
}
```

## License

See [LICENSE](LICENSE).
