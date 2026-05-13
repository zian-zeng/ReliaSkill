# ReliaSkill

<p align="center">
  <img src="docs/assets/reliaskill-wordmark.png" alt="ReliaSkill wordmark logo" width="720">
</p>

> **Core claim:** reliable tool use is not only a model problem. It is also a **representation problem**.

**ReliaSkill** is a pre-deployment reliability pipeline for MCP-style tool-use skills. It turns raw MCP-like schemas and sparse documentation into compact, schema-faithful, behavior-tested skill artifacts before downstream LLM agents ever see them.

Paper: **"ReliaSkill: From Raw MCP Schemas to Reliable Skills for Tool-Using LLM Agents"**


## Research Snapshot

Most tool-use failures do not begin when an agent emits malformed JSON. They begin earlier, when a tool is exposed through a representation that is **syntactically valid but operationally underspecified**. A raw MCP schema may list fields and types, yet still leave the model guessing about intent, scope, abstention, side effects, and argument construction.

ReliaSkill studies this missing layer. It treats each generated skill as a **candidate artifact**, not a trusted instruction. Before deployment, the artifact must preserve the schema, explain when the tool should and should not be used, pass structural checks, survive positive and adjacent negative controls, record repair traces, and receive an explicit gate decision.

<p align="center">
  <img src="docs/assets/reliaskill-overview.png" alt="ReliaSkill overview showing raw MCP schemas converted into reliable skill artifacts through validation, behavior tests, repair, and deployment gating.">
</p>

**Input:** raw MCP-like schemas and sparse docs.

**Output:** compact, inspected, behavior-tested skill artifacts with `DEPLOY`, `REPAIR`, or `REJECT` decisions.

**Research question:** how much reliability comes from giving the model a better-governed tool representation before it ever acts?

| Explore | What you will find |
| --- | --- |
| [Pipeline](#pipeline) | Six-stage normalization, generation, validation, behavior testing, repair, and gating. |
| [Datasets and controls](#datasets-and-controls) | MCP-like tools, converted benchmark schemas, synthetic tools, positive controls, and adjacent negatives. |
| [Reported results](#reported-results) | Seven-predictor evaluation results plus Qwen2.5-7B reliability ablations. |
| [Quick start](#quick-start) | Minimal commands for local packaging, reliability evaluation, routing, and tests. |

## The Short Version

Raw MCP schemas expose tool interfaces, but they rarely encode the agent-facing policy that matters in deployment:

- **When should this tool be used?**
- **When should the model abstain?**
- **How should arguments be assembled without inventing fields?**
- **How do we know a generated skill is safe enough to expose?**

ReliaSkill inserts a governed layer between protocol-level tool exposure and LLM tool invocation:

**Mental model:** `raw_mcp` -> `ToolIR++` -> `candidate skill` -> **validate** -> **test** -> **repair** -> **gate**

In practical terms, ReliaSkill asks: **what should happen before a new tool representation becomes visible to an agent?** The answer is not "generate a prettier prompt and hope." The answer is to treat the representation like a release candidate: inspect it, test it against real tool-use situations, try adjacent negative cases, repair localized failures, and only then decide whether it should be deployed.

| Instead of trusting... | ReliaSkill builds... |
| --- | --- |
| Thin raw schemas | Normalized ToolIR++ records with reliability metadata |
| Fluent one-shot skill text | Compact artifacts with explicit use and non-use boundaries |
| Unchecked examples | Schema-faithful examples and argument templates |
| Post-hoc debugging | Pre-deployment validation, repair, scoring, and gating |
| Utility-only evaluation | Positive controls plus adjacent negative controls |

**Output:** a deployability decision: `DEPLOY`, `REPAIR`, or `REJECT`.

ReliaSkill is intentionally focused. It is **not** a generic agent framework, an experience-rich skill-learning system, a GUI-agent skill ecosystem, or a trajectory distillation system.

## Why Raw Schemas Are Not Enough

The MCP ecosystem makes it easy to expose tools. That is powerful, but it creates a cold-start reliability problem: a newly exposed tool can be syntactically valid while still being a poor agent-facing representation. A schema can say that a `pattern` argument exists, but not whether the model should search for files, explain a file extension, abstain because the request is underspecified, or avoid a side-effecting action.

This project begins from a simple observation in the paper: **the boundary between "tool available" and "tool appropriate" is often missing.** ReliaSkill makes that boundary explicit and auditable.

- **Schemas are interfaces, not skills.** They specify accepted arguments, but not reliable use boundaries.
- **Sparse docs leave policy implicit.** Trigger conditions, preconditions, and abstention behavior are often missing.
- **Naive generated skills can be polished but wrong.** They may invent unsupported arguments, omit required fields, or over-broaden scope.
- **Over-triggering is a reliability bug.** A tool that fires on adjacent out-of-scope requests can be worse than no tool at all.
- **Tool onboarding should happen before deployment.** Generated skills are candidates that must pass validation, behavior tests, repair, and gating.

## The ReliaSkill Reliability Contract

A ReliaSkill artifact should be compact enough for an agent context, but explicit enough to be inspected. The pipeline tries to enforce a small reliability contract:

- **Schema-faithful:** no invented arguments, malformed examples, or unsupported enum values.
- **Boundary-aware:** clear when-to-use and when-not-to-use guidance.
- **Behavior-tested:** positive controls measure utility; adjacent negative controls measure over-triggering risk.
- **Repairable:** failures are localized into sections that can be patched without regenerating everything.
- **Gateable:** every candidate receives explicit evidence and a `DEPLOY`, `REPAIR`, or `REJECT` decision.

```mermaid
flowchart LR
  A[Raw MCP schema] --> B[ToolIR++ normalization]
  B --> C[Candidate skill artifact]
  C --> D{Structural validation}
  D -- pass --> E{Behavior controls}
  D -- fail --> R[Targeted repair]
  E -- utility + abstention evidence --> G{Deployment gate}
  E -- failure evidence --> R
  R --> D
  G -- DEPLOY --> P[Expose to downstream agent]
  G -- REPAIR --> R
  G -- REJECT --> X[Hold back]
```

## Visual Overview

| Why Raw Schemas Fail | ReliaSkill Pipeline |
| --- | --- |
| <img src="docs/assets/reliaskill-schema-failure.png" alt="Diagram showing missing use boundaries, sparse documentation, over-triggering, and invented arguments in raw schemas."> | <img src="docs/assets/reliaskill-pipeline.png" alt="Six-stage ReliaSkill pipeline from ToolIR++ normalization through deployment gating."> |

| Artifact Anatomy | Selected Result Highlights |
| --- | --- |
| <img src="docs/assets/reliaskill-artifact-anatomy.png" alt="Anatomy of a ReliaSkill artifact with use boundaries, argument template, examples, reports, repair trace, score, and deployment decision."> | <img src="docs/assets/reliaskill-results-highlights.png" alt="Reported result highlights comparing raw MCP, generated skills, boundary-first, and verbose-doc conditions."> |

## Pipeline

Generated skills are **not trusted by default**. ReliaSkill treats each skill as an artifact that must accumulate evidence before deployment.

| Stage | Description |
| --- | --- |
| 1. ToolIR++ normalization | Preserves the raw schema while adding provenance, documentation completeness, schema complexity, ambiguity, side-effect hints, and safety metadata. |
| 2. Compact skill generation | Produces purpose, when-to-use guidance, when-not-to-use guidance, argument templates, and schema-faithful examples. |
| 3. Structural validation | Checks unsupported arguments, missing required fields, enum errors, malformed examples, contradictory guidance, missing non-use boundaries, and compactness constraints. |
| 4. Behavior-grounded evaluation | Tests positive controls and adjacent negative controls so that tool-use gains are evaluated alongside abstention behavior. |
| 5. Targeted repair | Patches localized failing sections, such as examples, argument templates, or non-use boundaries, instead of regenerating the whole skill by default. |
| 6. Deployment gating | Emits `DEPLOY`, `REPAIR`, or `REJECT` from validation evidence, behavior evidence, repair traces, and reliability scoring. |

The most important design choice is the **repair loop**. ReliaSkill does not assume one-shot skill generation is reliable. It records validation failures, behavior failures, repair traces, and scores so that artifacts can be compared, audited, and rejected when needed.

## What This Repository Implements

| Area | Implemented support |
| --- | --- |
| **Schema ingestion** | MCP/tool schema parsing, normalization, and ToolIR++ reliability features. |
| **Skill construction** | Skill generation, prompt-template variants, compactness variants, and multi-candidate selection. |
| **Reliability checks** | Deterministic structural validation, behavior controls, targeted repair, and deploy/repair/reject gating. |
| **Evaluation** | Structured-call prediction, hidden-tool routing, hard distractor inventories, and positive/negative controls. |
| **Data conversion** | BFCL/API-style conversion and MCPToolBench++/ToolBench-style conversion when local data exists. |
| **Execution and analysis** | Sandbox live-execution subset, slice analysis, scientific comparison extraction, and low-compute scheduling. |
| **Backends** | `heuristic`, `openai_compatible`, and `local_hf` modes. |

## Who Should Care?

ReliaSkill is useful if you are studying or building:

- **Tool-using LLM agents** that need safer onboarding for new tools.
- **MCP servers or MCP-like tool collections** where raw schemas are too thin for robust agent use.
- **Function-calling evaluation** beyond simple argument matching.
- **Agent reliability research** that cares about abstention, adjacent negatives, routing, and side effects.
- **Low-compute experimentation** where smaller models need better representations rather than only larger checkpoints.

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

The prepared benchmark state includes:

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

The paper reports five main tool-facing representation conditions. Additional legacy and diagnostic conditions exist in saved logs and configs, but they are not part of the main paper framing.

| Condition | Representation exposed to the predictor |
| --- | --- |
| `raw_mcp` | The original MCP-like tool record: tool name, short description, and structured input schema. This is the "ship the schema as-is" baseline. |
| `generated_skill_base` | A generated skill artifact with purpose, use boundaries, non-use boundaries, an argument template, schema-faithful examples, semantic hints, and validation-aware candidate selection. It is the generator's base output, not an external AutoSkill baseline. |
| `curated_schema_reference` | A manually authored schema-reference skill from the same ToolIR++ source. This is a comparison point for careful manual authoring under the same structural conventions. |
| `skill_prompt_boundary_first` | The primary ReliaSkill rendering in the paper. It surfaces non-use boundaries before use guidance and keeps the exposed artifact compact. |
| `skill_prompt_verbose_docs` | A ReliaSkill rendering with more documentation-style narrative, additional examples, and informational notes. |

The two `skill_prompt_*` variants share the same underlying skill content and differ only in prompt rendering policy.

## Reported Results

The results should be read as a representation study, not a generic model leaderboard. Within each comparison, the downstream predictor is fixed and only the tool-facing representation changes.

### Main Results Across Seven Predictors

The evaluation compares five representation conditions under seven open-weight predictors on the same 1,475-control held-out test set. Values below are percentages.

#### Structured-Call Exact Match

| Condition | Llama3.2-1B | Qwen2.5-1.5B | Gemma2-2B | Phi-3.5-mini | Qwen2.5-7B | Llama3.1-8B | Gemma2-9B | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `raw_mcp` | 33.42 | 38.58 | 43.80 | 33.97 | 53.02 | 39.93 | 48.88 | 41.66 |
| `generated_skill_base` | 37.76 | 34.31 | 43.93 | 42.44 | 63.32 | 56.81 | 56.75 | 47.90 |
| `curated_schema_reference` | 38.71 | 37.29 | 30.37 | 32.61 | 53.83 | 37.69 | 46.78 | 39.61 |
| `skill_prompt_boundary_first` | **52.81** | **61.63** | 52.07 | **63.73** | **70.37** | **58.37** | **63.39** | **60.34** |
| `skill_prompt_verbose_docs` | 52.20 | 56.14 | **52.54** | 62.17 | 67.86 | 57.90 | 60.07 | 58.41 |

#### Hidden-Tool Routing Joint Exact

| Condition | Llama3.2-1B | Qwen2.5-1.5B | Gemma2-2B | Phi-3.5-mini | Qwen2.5-7B | Llama3.1-8B | Gemma2-9B | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `raw_mcp` | 22.24 | 14.44 | 21.02 | 25.22 | 34.31 | 27.86 | 34.03 | 25.59 |
| `generated_skill_base` | 26.24 | 17.02 | 26.98 | 31.32 | 42.24 | 39.39 | 38.71 | 31.70 |
| `curated_schema_reference` | 24.00 | 13.69 | 15.19 | 23.73 | 32.20 | 26.64 | 33.69 | 24.16 |
| `skill_prompt_boundary_first` | **37.76** | 31.53 | 31.80 | **45.29** | **45.42** | **42.03** | **44.07** | **39.70** |
| `skill_prompt_verbose_docs` | 35.19 | **33.02** | **34.03** | 42.71 | 44.75 | 40.07 | 41.29 | 38.72 |

### Qwen2.5-7B Component Ablation

The paper also isolates the Qwen2.5-7B reliability components. Full ReliaSkill gives the best Joint EM and Selection Accuracy. Argument Validity is not strictly monotonic: w/o Repair is slightly higher on local argument validity, while Full ReliaSkill is better on the joint objective.

| System | Joint EM | Argument Validity | Selection Accuracy |
| --- | ---: | ---: | ---: |
| Full ReliaSkill | **21.12%** | 52.78% | **31.39%** |
| w/o Repair | 20.41% | **53.05%** | 27.39% |
| w/o Validation | 18.85% | 50.07% | 27.36% |
| w/o Examples | 15.73% | 41.22% | 25.80% |

The Qwen2.5-7B reliability ladder improves Joint Exact Match from `raw_mcp` at 17.15% to Full ReliaSkill at 21.12%, a 23.1% relative gain over raw MCP exposure. Argument Validity improves from 43.66% to 52.78%.

## Key Takeaways From Current Results

- Raw schema exposure is the weakest main interface on average: 41.66% structured-call Exact Match and 25.59% routing Joint Exact.
- `generated_skill_base` improves the seven-model means by 6.24 and 6.11 absolute points, but the gain is not uniform across all predictors.
- `skill_prompt_boundary_first` is the primary ReliaSkill variant in the paper, reaching 60.34% structured-call Exact Match and 39.70% routing Joint Exact on average.
- `skill_prompt_verbose_docs` is close behind at 58.41% / 38.72%, and it wins routing Joint Exact for Qwen2.5-1.5B and Gemma2-2B.
- The ablation supports the paper's main claim: generated skills help, but validation, repair, and gating are needed to turn fluent skill text into a more reliable tool-facing representation.

## Reliability And Safety Notes

- Negative-control precision in the paper result should be interpreted as no observed harmful activation on the held-out negative controls, not as a production safety guarantee.
- After validation and repair, the reported artifact set has no residual checker-level failures: unsupported arguments, missing required fields, invalid enum values, malformed JSON examples, contradictory guidance, and missing non-use boundaries are all recorded as 0 / 2950.
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
