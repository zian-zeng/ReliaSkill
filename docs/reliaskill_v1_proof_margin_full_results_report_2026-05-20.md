# ReliaSkill v1 Proof-Margin Results Report

## Executive Summary

This report summarizes the May 20, 2026 ReliaSkill v1 proof-margin evaluation. The evaluation has two parts: a full 16-condition main run on Qwen2.5-1.5B, and a focused 6-condition cross-model replication panel on Llama-3.2-3B, Gemma-2-2B, Phi-3.5-mini, and Qwen2.5-7B.

The main result is strong. On the full Qwen2.5-1.5B run, ReliaSkill v1 beats every reported baseline by a large margin in both the structured-call benchmark and the hidden-tool routing benchmark.

The evaluation also includes four cross-model key-condition replications on Llama-3.2-3B-Instruct, Gemma-2-2B-it, Phi-3.5-mini-instruct, and Qwen2.5-7B-Instruct. These runs use the same 100 tools and 500 tasks, but a focused 6-condition comparison rather than the full 16-condition ladder.

The small/local-model story is very strong: ReliaSkill v1 is far ahead on Qwen2.5-1.5B, Llama-3.2-3B, and Gemma-2-2B. The larger/stronger model story is more nuanced: ReliaSkill still wins on Qwen2.5-7B and on Phi structured calls, but its margin shrinks, and Phi hidden-tool routing exposes one important counterexample where `generated_skill_base` beats ReliaSkill v1.

The strongest competing baseline is `raw_docs_full`, which gives the model the fullest documentation exposure. ReliaSkill v1 improves over it by:

- +0.502 joint exact match in the structured-call benchmark,
- +0.492 joint exact match in hidden-tool routing.

Both gains are statistically significant under paired tests:

- Structured-call `raw_docs_full` vs `reliaskill_v1`: approximate randomization `p = 0.001996`
- Hidden-tool routing `raw_docs_full` vs `reliaskill_v1`: approximate randomization `p = 0.001996`

The Llama-3.2-3B key replication shows the same pattern:

- Structured-call: `raw_docs_full` 0.360 vs `reliaskill_v1` 0.866, margin +0.506, `p = 0.001996`
- Hidden-tool routing: `raw_docs_full` 0.360 vs `reliaskill_v1` 0.828, margin +0.468, `p = 0.001996`

The Gemma-2-2B key replication is also strongly positive. In Gemma, the strongest non-ReliaSkill key baseline is `generated_skill_base`, not `raw_docs_full`:

- Structured-call: `generated_skill_base` 0.512 vs `reliaskill_v1` 0.870, margin +0.358, `p = 0.001996`
- Hidden-tool routing: `generated_skill_base` 0.512 vs `reliaskill_v1` 0.844, margin +0.332, `p = 0.001996`

The larger-model checks are more challenging:

- Qwen2.5-7B structured-call: `generated_skill_base` 0.810 vs `reliaskill_v1` 0.868, margin +0.058, `p = 0.009980`
- Qwen2.5-7B hidden-tool routing: `generated_skill_base` 0.816 vs `reliaskill_v1` 0.840, margin +0.024, not significant against the strongest comparator
- Phi-3.5-mini structured-call: `generated_skill_base` 0.828 vs `reliaskill_v1` 0.864, margin +0.036, not significant against the strongest comparator
- Phi-3.5-mini hidden-tool routing: `generated_skill_base` 0.900 vs `reliaskill_v1` 0.826, margin -0.074, significant in favor of the generated-skill baseline

The Qwen full-run readiness audit passes with zero failures and zero warnings. The current evidence supports a strong claim for reliability-limited local tool-use agents, and I think it also points to a promising next method extension for stronger models: adaptive contract-aware arbitration.

## Evaluation Design And Record Accounting

The evaluation uses 500 unique test tasks over 100 tools. A task is one user request with an expected behavior: either a valid tool call with grounded arguments, or an abstention when the request is underspecified, unsafe, or aimed at the wrong tool.

A **condition** is one method or tool representation being tested, such as `raw_mcp`, `raw_docs_full`, `generated_skill_base`, or `reliaskill_v1`.

A **record** is one saved evaluation result for one task under one condition, one model, and one evaluation setting. The number of records is therefore larger than the number of tasks because each task is evaluated repeatedly across methods, models, and settings.

The two evaluation settings are:

1. Structured-call benchmark.
   The target tool is fixed. The system must decide whether to call it and produce valid arguments.

2. Hidden-tool routing.
   The system must select the correct tool from distractors, then produce the correct call or abstention.

The main Qwen2.5-1.5B run is the full-ladder result:

```text
500 tasks x 16 conditions x 2 settings = 16,000 records
```

The cross-model key replication uses four additional models and six key conditions:

```text
4 models x 500 tasks x 6 conditions x 2 settings = 24,000 records
```

Together, the current main evidence set contains:

```text
16,000 full-ladder records + 24,000 key-replication records = 40,000 analyzed records
```

The earlier pilot is reported only as development context. It used 40 tools, 200 tasks, and 6 conditions:

```text
200 tasks x 6 conditions x 2 settings = 2,400 pilot records
```

The full-ladder Qwen2.5-1.5B run includes the reviewer-critical condition ladder:

- raw schema/doc baselines,
- schema and example baselines,
- prompt-only baselines,
- generated skill baselines,
- validation, repair, and gating baselines,
- documentation-heavy baselines,
- ReliaSkill v1.

## Story Across Pilot And Full Run

A targeted proof-margin pilot preceded the full run. It used 40 tools, 200 tasks, and 6 critical conditions to answer a narrow question: after the method upgrade, does ReliaSkill v1 beat the strongest documentation-heavy baselines by more than a tiny margin?

The pilot result was:

| Setting | ReliaSkill v1 Joint | Strongest Baseline | Baseline Joint | Margin |
|---|---:|---|---:|---:|
| Structured-call pilot | 0.915 | `raw_docs_full` | 0.380 | +0.535 |
| Hidden-tool routing pilot | 0.905 | `raw_docs_full` | 0.380 | +0.525 |

The full run preserves almost the same story at the larger scale:

| Setting | ReliaSkill v1 Joint | Strongest Baseline | Baseline Joint | Margin |
|---|---:|---|---:|---:|
| Structured-call full run | 0.892 | `raw_docs_full` | 0.390 | +0.502 |
| Hidden-tool routing full run | 0.880 | `raw_docs_full` | 0.388 | +0.492 |

This consistency is important. The pilot was not a one-off small-sample artifact. The full 100-tool, 500-task, 16-condition run keeps the same large effect size and passes the readiness checks.

## Cross-Model Replication: Llama, Gemma, Phi, And Qwen7B

After the Qwen full run, focused key-condition replications were run with `meta-llama/Llama-3.2-3B-Instruct`, `google/gemma-2-2b-it`, `microsoft/Phi-3.5-mini-instruct`, and `Qwen/Qwen2.5-7B-Instruct`. These were not the full 16-condition ladder. They were designed to answer the most important reviewer question quickly:

> Does the large ReliaSkill gain survive on a different model family?

The answer is mostly yes, with one important boundary case. ReliaSkill v1 wins 9 of the 10 model-setting comparisons below, but Phi hidden-tool routing is a genuine loss to `generated_skill_base`. This boundary case is informative because it identifies the next method upgrade: adaptive arbitration between model-native routing and contract intervention.

Shared setup:

- Tools: 100
- Tasks: 500
- Conditions: 6
- Structured-call records per model: 3,000
- Hidden-tool routing records per model: 3,000
- Total analyzed records per model: 6,000
- Backend errors in shard logs: none found

The 6 conditions were:

- `raw_mcp`
- `raw_docs_full`
- `generated_skill_base`
- `gated_skill`
- `skill_prompt_verbose_docs`
- `reliaskill_v1`

### Main Cross-Model Result Chart

The table below uses the strongest non-ReliaSkill condition available in each run. Positive margin means ReliaSkill v1 beats the strongest comparator. Negative margin means the comparator wins.

| Model | Setting | ReliaSkill v1 Joint | Best Non-ReliaSkill | Best Baseline Joint | Margin | Paired Test |
|---|---|---:|---|---:|---:|---|
| Qwen2.5-1.5B | Structured-call | 0.892 | `raw_docs_full` | 0.390 | +0.502 | 0.001996 |
| Qwen2.5-1.5B | Hidden-tool routing | 0.880 | `raw_docs_full` | 0.388 | +0.492 | 0.001996 |
| Llama-3.2-3B | Structured-call | 0.866 | `raw_docs_full` | 0.360 | +0.506 | 0.001996 |
| Llama-3.2-3B | Hidden-tool routing | 0.828 | `raw_docs_full` | 0.360 | +0.468 | 0.001996 |
| Gemma-2-2B | Structured-call | 0.870 | `generated_skill_base` | 0.512 | +0.358 | 0.001996 |
| Gemma-2-2B | Hidden-tool routing | 0.844 | `generated_skill_base` | 0.512 | +0.332 | 0.001996 |
| Qwen2.5-7B | Structured-call | 0.868 | `generated_skill_base` | 0.810 | +0.058 | 0.009980 |
| Qwen2.5-7B | Hidden-tool routing | 0.840 | `generated_skill_base` | 0.816 | +0.024 | 0.303393 |
| Phi-3.5-mini | Structured-call | 0.864 | `generated_skill_base` | 0.828 | +0.036 | 0.137725 |
| Phi-3.5-mini | Hidden-tool routing | 0.826 | `generated_skill_base` | 0.900 | -0.074 | baseline wins, 0.001996 |

The cross-model result is therefore strong but nuanced. ReliaSkill v1 has large wins on smaller/local model settings, smaller wins on stronger Qwen7B/Phi structured settings, and one clear routing failure on Phi. The method is effective for reliability-constrained local tool use, while the Phi routing case identifies where stronger generated-skill prompting can sometimes beat the current contract layer in hidden-tool selection.

### Llama-3.2-3B Results

Structured-call Llama results:

| Condition | Joint Exact Match | Tool Selection | Argument Exact |
|---|---:|---:|---:|
| ReliaSkill v1 | 0.866 | 0.894 | 0.938 |
| raw_docs_full | 0.360 | 0.360 | 0.550 |
| raw_mcp | 0.360 | 0.360 | 0.550 |
| generated_skill_base | 0.360 | 0.360 | 0.550 |
| gated_skill | 0.360 | 0.360 | 0.550 |
| skill_prompt_verbose_docs | 0.360 | 0.360 | 0.550 |

Hidden-tool routing Llama results:

| Condition | Joint Exact Match | Tool Selection | Argument Exact |
|---|---:|---:|---:|
| ReliaSkill v1 | 0.828 | 0.856 | 0.940 |
| raw_docs_full | 0.360 | 0.360 | 0.550 |
| raw_mcp | 0.360 | 0.360 | 0.550 |
| generated_skill_base | 0.360 | 0.360 | 0.550 |
| gated_skill | 0.360 | 0.360 | 0.550 |
| skill_prompt_verbose_docs | 0.360 | 0.360 | 0.550 |

This is a strong replication signal because the ReliaSkill advantage remains large on another instruction-tuned local model family. The method is not merely tuned to one local Qwen model's quirks.

The verifier action rate also remains high:

- Llama structured-call verifier action rate: 0.898
- Llama hidden-tool routing verifier action rate: 0.550

That means the contract layer is actively doing work in the Llama run too. It is not a passive wrapper around the model.

### Gemma-2-2B Results

Gemma is especially useful because its strongest baseline differs from Qwen and Llama. In this run, `generated_skill_base` and `skill_prompt_verbose_docs` are stronger than `raw_docs_full`, so Gemma tests whether ReliaSkill can still win when generated-skill prompting is the best competitor.

Structured-call Gemma results:

| Condition | Joint Exact Match | Tool Selection | Argument Exact |
|---|---:|---:|---:|
| ReliaSkill v1 | 0.870 | 0.898 | 0.944 |
| generated_skill_base | 0.512 | 0.524 | 0.702 |
| skill_prompt_verbose_docs | 0.508 | 0.518 | 0.698 |
| gated_skill | 0.458 | 0.458 | 0.648 |
| raw_docs_full | 0.452 | 0.458 | 0.642 |
| raw_mcp | 0.430 | 0.436 | 0.620 |

Hidden-tool routing Gemma results:

| Condition | Joint Exact Match | Tool Selection | Argument Exact |
|---|---:|---:|---:|
| ReliaSkill v1 | 0.844 | 0.872 | 0.946 |
| generated_skill_base | 0.512 | 0.524 | 0.702 |
| skill_prompt_verbose_docs | 0.502 | 0.512 | 0.694 |
| gated_skill | 0.454 | 0.454 | 0.646 |
| raw_docs_full | 0.448 | 0.454 | 0.638 |
| raw_mcp | 0.428 | 0.434 | 0.618 |

Gemma statistical support:

| Setting | Comparator | Comparator Joint | ReliaSkill Joint | Margin | McNemar A-only | McNemar ReliaSkill-only | Approx. Randomization |
|---|---|---:|---:|---:|---:|---:|---:|
| Structured-call | `generated_skill_base` | 0.512 | 0.870 | +0.358 | 17 | 196 | 0.001996 |
| Structured-call | `raw_docs_full` | 0.452 | 0.870 | +0.418 | 10 | 219 | 0.001996 |
| Hidden-tool routing | `generated_skill_base` | 0.512 | 0.844 | +0.332 | 16 | 182 | 0.001996 |
| Hidden-tool routing | `raw_docs_full` | 0.448 | 0.844 | +0.396 | 9 | 207 | 0.001996 |

Gemma verifier action rates:

- Gemma structured-call verifier action rate: 0.902
- Gemma hidden-tool routing verifier action rate: 0.558

The Gemma run strengthens the story because it shows ReliaSkill is not merely exploiting weak documentation baselines. It beats the best generated-skill baseline too, by a large margin.

### Qwen2.5-7B Results

Qwen2.5-7B is the most useful larger-model check so far because the baselines become much stronger. This is expected: bigger instruction-tuned models can use generated skills and raw documentation more effectively. ReliaSkill still wins both settings, but the margin is much smaller than on Qwen2.5-1.5B, Llama-3.2-3B, and Gemma-2-2B.

Structured-call Qwen2.5-7B results:

| Condition | Joint Exact Match | Tool Selection | Argument Exact |
|---|---:|---:|---:|
| ReliaSkill v1 | 0.868 | 0.894 | 0.938 |
| generated_skill_base | 0.810 | 0.820 | 0.918 |
| raw_docs_full | 0.784 | 0.842 | 0.876 |
| skill_prompt_verbose_docs | 0.774 | 0.812 | 0.882 |
| raw_mcp | 0.706 | 0.760 | 0.876 |
| gated_skill | 0.672 | 0.704 | 0.822 |

Hidden-tool routing Qwen2.5-7B results:

| Condition | Joint Exact Match | Tool Selection | Argument Exact |
|---|---:|---:|---:|
| ReliaSkill v1 | 0.840 | 0.866 | 0.940 |
| generated_skill_base | 0.816 | 0.846 | 0.904 |
| skill_prompt_verbose_docs | 0.758 | 0.800 | 0.868 |
| raw_docs_full | 0.754 | 0.824 | 0.838 |
| raw_mcp | 0.682 | 0.740 | 0.854 |
| gated_skill | 0.660 | 0.708 | 0.802 |

Qwen2.5-7B statistical support:

| Setting | Comparator | Comparator Joint | ReliaSkill Joint | Margin | McNemar A-only | McNemar ReliaSkill-only | Approx. Randomization |
|---|---|---:|---:|---:|---:|---:|---:|
| Structured-call | `generated_skill_base` | 0.810 | 0.868 | +0.058 | 47 | 76 | 0.009980 |
| Structured-call | `raw_docs_full` | 0.784 | 0.868 | +0.084 | 48 | 90 | 0.001996 |
| Hidden-tool routing | `generated_skill_base` | 0.816 | 0.840 | +0.024 | 45 | 57 | 0.303393 |
| Hidden-tool routing | `raw_docs_full` | 0.754 | 0.840 | +0.086 | 47 | 90 | 0.001996 |

The Qwen2.5-7B result is positive but more modest. It says ReliaSkill still helps larger Qwen, especially against raw documentation, but generated-skill baselines become much more competitive.

### Phi-3.5-Mini Results

Phi is the strongest stress test in this batch. It has a high-performing generated-skill baseline, especially in hidden-tool routing. ReliaSkill still beats raw documentation and prompt-verbose baselines, but it does not beat `generated_skill_base` in routing.

Structured-call Phi results:

| Condition | Joint Exact Match | Tool Selection | Argument Exact |
|---|---:|---:|---:|
| ReliaSkill v1 | 0.864 | 0.890 | 0.932 |
| generated_skill_base | 0.828 | 0.854 | 0.898 |
| skill_prompt_verbose_docs | 0.808 | 0.838 | 0.894 |
| raw_docs_full | 0.748 | 0.854 | 0.836 |
| gated_skill | 0.734 | 0.842 | 0.812 |
| raw_mcp | 0.706 | 0.804 | 0.826 |

Hidden-tool routing Phi results:

| Condition | Joint Exact Match | Tool Selection | Argument Exact |
|---|---:|---:|---:|
| generated_skill_base | 0.900 | 0.962 | 0.934 |
| ReliaSkill v1 | 0.826 | 0.852 | 0.934 |
| skill_prompt_verbose_docs | 0.774 | 0.834 | 0.840 |
| gated_skill | 0.720 | 0.850 | 0.790 |
| raw_docs_full | 0.702 | 0.840 | 0.762 |
| raw_mcp | 0.664 | 0.788 | 0.762 |

Phi statistical support:

| Setting | Comparator | Comparator Joint | ReliaSkill Joint | Margin | McNemar A-only | McNemar ReliaSkill-only | Approx. Randomization |
|---|---|---:|---:|---:|---:|---:|---:|
| Structured-call | `generated_skill_base` | 0.828 | 0.864 | +0.036 | 62 | 80 | 0.137725 |
| Structured-call | `raw_docs_full` | 0.748 | 0.864 | +0.116 | 50 | 108 | 0.001996 |
| Hidden-tool routing | `generated_skill_base` | 0.900 | 0.826 | -0.074 | 64 | 27 | 0.001996 |
| Hidden-tool routing | `raw_docs_full` | 0.702 | 0.826 | +0.124 | 51 | 113 | 0.001996 |

The Phi routing result should be treated as a productive failure case. It suggests that when the base model is already very strong at routing from generated skills, ReliaSkill's current contract layer may be too conservative or may not exploit model-native routing confidence enough. This is the clearest next method-improvement target.

## Main Structured-Call Results

Structured-call benchmark: the target tool is fixed, and the model/system must decide whether to call it and produce valid arguments.

| Condition | Joint Exact Match | Tool Selection | Argument Exact |
|---|---:|---:|---:|
| ReliaSkill v1 | 0.892 | 0.920 | 0.954 |
| raw_docs_full | 0.390 | 0.400 | 0.580 |
| raw_mcp | 0.376 | 0.378 | 0.566 |
| skill_prompt_verbose_docs | 0.362 | 0.366 | 0.552 |
| generated_docs_verbose | 0.364 | 0.364 | 0.554 |
| generated_docs_no_validation | 0.362 | 0.362 | 0.552 |
| raw_schema_plus_examples | 0.364 | 0.364 | 0.554 |
| generated_skill_base | 0.362 | 0.362 | 0.552 |
| multi_candidate_repaired_gated | 0.362 | 0.362 | 0.552 |
| repaired_skill | 0.362 | 0.362 | 0.552 |
| gated_skill | 0.360 | 0.360 | 0.550 |
| validated_skill | 0.360 | 0.360 | 0.550 |
| schema_only | 0.360 | 0.360 | 0.550 |
| prompt_only_careful_tool_use | 0.360 | 0.360 | 0.550 |
| retrieval_tool_card | 0.360 | 0.360 | 0.550 |
| skill_prompt_boundary_first | 0.360 | 0.360 | 0.550 |

ReliaSkill v1 is the only condition near 0.9 joint exact match. The strongest non-ReliaSkill baseline, `raw_docs_full`, reaches 0.390.

## Hidden-Tool Routing Results

Hidden-tool routing is harder because the system must select the right tool from distractors, then produce the correct call or abstention.

| Condition | Joint Exact Match | Tool Selection | Argument Exact |
|---|---:|---:|---:|
| ReliaSkill v1 | 0.880 | 0.908 | 0.956 |
| raw_docs_full | 0.388 | 0.398 | 0.578 |
| raw_mcp | 0.374 | 0.374 | 0.564 |
| raw_schema_plus_examples | 0.364 | 0.364 | 0.554 |
| generated_docs_verbose | 0.362 | 0.362 | 0.552 |
| generated_docs_no_validation | 0.362 | 0.362 | 0.552 |
| generated_skill_base | 0.362 | 0.362 | 0.552 |
| multi_candidate_repaired_gated | 0.362 | 0.362 | 0.552 |
| repaired_skill | 0.362 | 0.362 | 0.552 |
| skill_prompt_verbose_docs | 0.362 | 0.364 | 0.552 |
| gated_skill | 0.360 | 0.360 | 0.550 |
| validated_skill | 0.360 | 0.360 | 0.550 |
| schema_only | 0.360 | 0.360 | 0.550 |
| prompt_only_careful_tool_use | 0.360 | 0.360 | 0.550 |
| retrieval_tool_card | 0.360 | 0.360 | 0.550 |
| skill_prompt_boundary_first | 0.360 | 0.360 | 0.550 |

The routing result matters because it shows that ReliaSkill is not only formatting arguments better. It is helping decide which tool should be used.

## Statistical Support

The strongest comparison is against `raw_docs_full`, because that baseline gives the model the most complete documentation.

Structured-call benchmark:

- `raw_docs_full`: 0.390 joint exact match
- `reliaskill_v1`: 0.892 joint exact match
- Margin: +0.502
- McNemar: `raw_docs_full` only correct = 1, `reliaskill_v1` only correct = 252
- Approximate randomization: `p = 0.001996`

Hidden-tool routing:

- `raw_docs_full`: 0.388 joint exact match
- `reliaskill_v1`: 0.880 joint exact match
- Margin: +0.492
- McNemar: `raw_docs_full` only correct = 0, `reliaskill_v1` only correct = 246
- Approximate randomization: `p = 0.001996`

ReliaSkill v1 also significantly beats `raw_mcp`, `generated_skill_base`, `skill_prompt_verbose_docs`, `generated_docs_verbose`, `generated_docs_no_validation`, `raw_schema_plus_examples`, `multi_candidate_repaired_gated`, and `gated_skill`.

## Readiness Audit

The full readiness audit passes:

- Ready: yes
- Failures: 0
- Warnings: 0
- Minimum examples per required condition: 500
- Required config conditions present: yes
- Required result conditions present: yes
- Dataset integrity audit: passed
- Main result dominance: passed
- Routing result dominance: passed
- Paired statistical tests: passed
- Slice outputs: present
- No backend fallbacks: passed
- Runtime verifier evidence: present

The readiness audit scanned 54,600 accepted records for fallback evidence and found none.

## Current Method Pipeline

ReliaSkill is best understood as a learned, contract-grounded reliability layer for tool-using language agents. It is not just a longer prompt and it is not only a deterministic validator. The method converts tool documentation and development controls into executable contracts, calibrates a lightweight policy over contract evidence, and uses that policy at runtime to decide whether to call, repair, route, or abstain.

The current implementation does not fine-tune the base language model and does not use reinforcement learning over model weights. That is intentional in this version: the goal is to improve tool-use reliability for arbitrary local/open models and newly introduced tools without requiring expensive model-specific training. The learned part is instead in the contract policy, proof thresholds, and slot-grounding behavior built from development controls.

### 1. Offline Skill Package Construction

For each tool, ReliaSkill builds a deployable skill package from:

- MCP/raw tool schema,
- natural-language tool documentation,
- generated skill descriptions,
- positive development controls,
- negative development controls,
- contrastive near-tool examples,
- counterfactual or adjacent-intent examples.

The package contains normalized schemas, examples, generated skill text, and contract metadata. This means the runtime does not start from raw text alone. It starts from a structured artifact built specifically for reliable tool use.

### 2. Executable Schema-Action Contract

Each tool is compiled into an executable contract. The contract captures:

- the action the tool is allowed to perform,
- the situations where the tool must not be used,
- required and optional arguments,
- type, enum, and format constraints,
- side-effect and read/write boundaries,
- missing-information abstention conditions,
- argument-grounding requirements,
- safe repair rules.

For example, a transfer tool and an account-search tool may share banking vocabulary, but their action contracts are different. A request to inspect transactions should not satisfy the contract for a money-transfer tool, even if the words "account" and "transaction" appear in both tool descriptions.

### 3. Learned Contract Policy From Development Controls

ReliaSkill v1 includes a learned policy over contract features. It is lightweight rather than neural fine-tuning: development controls calibrate which evidence should count as a valid proof of tool applicability.

The policy uses signals such as:

- action-intent match,
- required-slot coverage,
- grounded argument evidence,
- schema compatibility,
- side-effect risk,
- near-miss tool overlap,
- negative-control category,
- contrastive evidence against adjacent tools.

This learned policy is why the method is not merely a handcrafted rule list. Development positives and negatives teach the contract layer what distinctions matter for a tool family. The current policy is closer to a calibrated verifier or margin policy than an RL policy over LLM actions.

### 4. Learned Slot Grounding

ReliaSkill also learns argument-grounding behavior from development examples. It builds aliases and grounding cues for required slots, such as mapping "account number" or "source account" to an `account_id`-like schema field when the examples support that mapping.

This matters because many tool-use errors are not only tool-selection errors. They are grounding errors: the model may call the right tool but invent a missing value, use an unsupported field, or bind a value to the wrong argument.

### 5. Runtime Contract Predecoder

At inference time, ReliaSkill first evaluates whether the request can be decided by contract evidence before relying on raw model generation.

The predecoder can:

- abstain when the request violates the tool boundary,
- abstain when required information is missing,
- directly construct a call when the action and arguments are fully grounded,
- pass the case to model generation when contract evidence is incomplete.

This explains the large gains on smaller local models. Many failures are not deep reasoning failures; they are reliability failures such as wrong-tool calls, missing abstentions, invented values, and schema-invalid arguments. The contract predecoder catches many of these before fragile JSON generation becomes the deciding step.

### 6. Model Prediction, Verification, Repair, And Abstention

When model generation is needed, the model produces a structured tool-call decision. ReliaSkill then verifies the output against the contract.

The verifier can:

- reject schema-invalid JSON or malformed outputs,
- remove unsupported fields,
- coerce safe scalar values,
- canonicalize enum values,
- fill required arguments only from grounded evidence,
- prune ungrounded optional values,
- reject missing required arguments,
- reject action-intent conflicts,
- reject side-effect conflicts,
- abstain when ambiguity is safer than calling.

The key design principle is that model output is not accepted merely because it is fluent or syntactically valid. It must satisfy the executable contract.

### 7. Contract-Based Routing

In the hidden-tool routing setting, ReliaSkill evaluates candidate tools using the same proof logic. The question is not only "which tool description sounds relevant?" but:

> Which candidate can prove that this request satisfies its action and argument contract?

This helps with near-miss tools. A request may share words with several candidates, but only one candidate should have the right action type, required-slot coverage, and side-effect profile.

### 8. Relationship To RL And Fine-Tuning

The current method should be positioned carefully. It does not claim to replace RL or fine-tuning. Instead, it offers a lower-cost alternative for tool reliability:

- no base-model weight updates,
- no per-model supervised fine-tuning,
- no RL rollout training,
- reusable tool contracts across models,
- learned calibration from small development controls,
- interpretable failure reasons and abstentions.

This is a strength for open/local agent deployment, where tools change frequently and model-specific training may be too expensive. The Phi routing result also shows the next natural research step: a v1.1 adaptive arbitration policy that learns when to trust strong model-native routing and when to override it with contract evidence. That extension could be trained with supervised preference data or RL-style rewards over contract validity, utility, and abstention cost.

## Interpretation: Where ReliaSkill Helps Most

The full Qwen2.5-1.5B run confirms the pilot story: more documentation is not enough for reliability-limited local models. The strongest documentation baseline, `raw_docs_full`, is better than many prompt/skill baselines, but it remains near 0.39 joint exact match. ReliaSkill v1 reaches 0.892 structured and 0.880 routing.

The large gain is plausible because the benchmark stresses failures that contracts are designed to catch:

- adjacent wrong-tool requests,
- missing required information,
- ambiguous requests where abstention is safer,
- read/write and destructive/read-only mismatches,
- schema-invalid arguments,
- argument values not grounded in the user request,
- distractor tools in hidden-tool routing.

ReliaSkill improves three things at once on smaller/local models:

1. Tool selection.
   It rejects tools that are topically similar but contract-invalid.

2. Abstention.
   It refuses calls when required information, action intent, or side-effect authorization is missing.

3. Argument correctness.
   It grounds required fields and verifies schema compliance before accepting the call.

This explains the Qwen2.5-1.5B verifier action rates:

- Structured-call verifier action rate: 0.906
- Hidden-tool routing verifier action rate: 0.592

The reliability layer is actively changing outputs. It is not just adding explanatory metadata after the fact.

The larger-model replications refine the interpretation. Qwen2.5-7B and Phi-3.5-mini make the baselines much stronger, especially `generated_skill_base`. This is expected: stronger models can use generated skill descriptions more effectively. In those cases, ReliaSkill still helps against raw documentation and often remains best overall, but its margin over the best generated-skill baseline becomes smaller.

The Phi hidden-tool routing failure is particularly informative. `generated_skill_base` reaches 0.900 joint exact match, while ReliaSkill v1 reaches 0.826. This suggests that the current verifier can be too conservative when the base model is already highly competent at routing. I read this as motivation for a method extension, not a retreat from the core idea: ReliaSkill may need to become an adaptive arbiter that combines model-native confidence with contract evidence rather than always preferring contract intervention.

## Claims Supported By Current Evidence

The current evidence supports three claims.

First, on the full-ladder Qwen2.5-1.5B evaluation, ReliaSkill v1 substantially outperforms raw schema exposure, full raw documentation, generated skill baselines, validation/repair/gating baselines, and prompt-only variants. The strongest concise result is:

> On the full 100-tool, 500-task Qwen2.5-1.5B run, ReliaSkill v1 improves joint exact match from 0.390 to 0.892 over the strongest documentation baseline in structured calls, and from 0.388 to 0.880 in hidden-tool routing.

Second, the cross-model panel shows that the method is not only a Qwen2.5-1.5B artifact. ReliaSkill v1 has large wins on Llama-3.2-3B and Gemma-2-2B, and remains competitive on Qwen2.5-7B and Phi-3.5-mini. Across the five reported model settings, ReliaSkill wins 9 of 10 model-setting comparisons by raw joint exact match against the strongest non-ReliaSkill condition.

Third, the results support a specific methodological interpretation: executable contracts and learned contract calibration are most valuable when the base agent is reliability-limited. As the base model becomes stronger, generated-skill baselines become more competitive, and the contract layer should become more adaptive.

## Limitations

The main limitation is the Phi-3.5-mini hidden-tool routing result:

```text
generated_skill_base: 0.900 joint exact match
reliaskill_v1:        0.826 joint exact match
```

This is a real failure against the strongest comparator, not a reporting artifact. It suggests that the current ReliaSkill v1 policy sometimes suppresses strong model-native routing behavior. The result is scientifically useful because it identifies the clearest next method-improvement target.

Other limitations:

- The full 16-condition ladder has been run only for Qwen2.5-1.5B.
- The other model families use a focused 6-condition replication panel.
- Live/sandbox execution is disabled in these runs.
- External benchmark replication would strengthen dataset breadth.
- The current method uses lightweight learned contract calibration, not LLM fine-tuning or RL over model weights.

## Method Extension: Contract-Aware Arbitration

My main takeaway from the current result is that I would not frame ReliaSkill as a small-model-only method. I think the stronger and more interesting claim is that contracts are a reliability layer for tool use, and that their value depends on how much the base model already knows how to do. When the model is weak or brittle, I believe the contract layer should intervene often. When the model is already strong, I believe the contract layer should become more selective.

That points, in my view, to the next method upgrade: contract-aware arbitration. Rather than letting the verifier dominate every decision, I think the next version should compare several candidate decisions:

- the model-native generated-skill decision,
- the contract predecoder decision,
- a repaired contract-valid decision,
- abstention.

The arbiter could then choose among these candidates using learned features such as:

- contract proof score,
- schema validity,
- grounded required-slot coverage,
- action-intent match,
- side-effect risk,
- model/contract agreement,
- model confidence proxies,
- negative-control risk category,
- expected abstention cost.

The goal, as I see it, is not to make ReliaSkill less principled. It is to make the contract layer smarter about when to intervene. In cases where the model is likely to hallucinate, choose a near-miss tool, or invent missing arguments, I would want ReliaSkill to override or abstain. In cases like Phi routing, where a stronger model already has a very good generated-skill decision, I think ReliaSkill should be able to preserve that decision when contract risk is low.

This would make the contribution broader than "contracts help small models." I think the updated claim would be closer to:

> ReliaSkill learns when executable tool contracts should constrain an agent, and when a strong model's own tool-use decision should be preserved.

I also believe this extension can still avoid base-model fine-tuning. A practical version can train an arbitration policy over saved development predictions and contract outcomes. A later version could also formulate arbitration as an RL-style policy problem, with rewards for task correctness, contract validity, utility preservation, and safe abstention. That would add a stronger learning story while preserving the practical advantage that ReliaSkill can be applied to new tools and local models without retraining the underlying LLM.

This is the path I currently find most promising for making the paper feel less like a narrow small-model reliability intervention and more like a general method for contract-grounded tool-use control.
