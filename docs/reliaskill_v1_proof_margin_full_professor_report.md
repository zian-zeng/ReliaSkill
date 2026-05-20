# ReliaSkill v1 Proof-Margin Full Run Report

## Executive Summary

We completed the clean full Qwen2.5-1.5B ReliaSkill v1 proof-margin run after the method upgrade. The result is strong and consistent with the earlier pilot: ReliaSkill v1 beats every reported baseline by a large margin in both the structured-call benchmark and the hidden-tool routing benchmark.

The strongest competing baseline is `raw_docs_full`, which gives the model the fullest documentation exposure. ReliaSkill v1 improves over it by:

- +0.502 joint exact match in the structured-call benchmark,
- +0.492 joint exact match in hidden-tool routing.

Both gains are statistically significant under paired tests:

- Structured-call `raw_docs_full` vs `reliaskill_v1`: approximate randomization `p = 0.001996`
- Hidden-tool routing `raw_docs_full` vs `reliaskill_v1`: approximate randomization `p = 0.001996`

The readiness audit passes with zero failures and zero warnings. This is no longer only a pilot. It is a claim-ready single-model result on the main mixed-source ReliaSkill benchmark suite.

## Artifact Provenance

Full-run archive:

`outputs/frozen_results/reliaskill_v1_proof_margin_full_results_20260520_100412.tar.gz`

Extracted full-run artifacts:

`outputs/overnight_qwen15b_4gpu_reliaskill_v1_proof_margin`

Config:

`configs/experiments/overnight_qwen15b_4gpu_reliaskill_v1_proof_margin.yaml`

This report was verified against the extracted local artifacts:

- `tables/main_results.csv`
- `tables/routing_results.csv`
- `tables/stat_tests.csv`
- `tables/routing_stat_tests.csv`
- `merged/cluster_merge_manifest.json`
- `reliaskill_readiness_full.md`
- `slice_analysis_summary.md`

## Full Run Setup

- Model: `Qwen/Qwen2.5-1.5B-Instruct`, local HF, 4-bit
- Tools: 100
- Tasks: 500
- Conditions: 16
- Structured-call records: 8,000
- Hidden-tool routing records: 8,000
- Total analyzed records: 16,000
- Live execution: disabled for this run
- Backend fallbacks: none
- Dataset integrity audit: passed
- Readiness audit: ready, zero failures, zero warnings

### Why 500 Tasks Become 16,000 Records

The run has 500 unique evaluation tasks, but each task is evaluated many times.

A **task** is one user request with an expected behavior. For example, a task may ask for a specific tool call, or it may be a negative control where the correct behavior is to abstain.

A **condition** is one representation or method being tested, such as `raw_mcp`, `raw_docs_full`, `generated_skill_base`, or `reliaskill_v1`.

A **record** is one saved evaluation result for one task under one condition in one evaluation setting.

This full run has:

- 500 tasks,
- 16 conditions,
- 2 evaluation settings.

So the total number of saved result records is:

```text
500 tasks x 16 conditions x 2 settings = 16,000 records
```

The two settings are:

1. Structured-call benchmark.
   The target tool is fixed. The system must decide whether to call it and produce valid arguments.

2. Hidden-tool routing.
   The system must select the correct tool from distractors, then produce the correct call or abstention.

Therefore:

```text
500 tasks x 16 conditions = 8,000 structured-call records
500 tasks x 16 conditions = 8,000 hidden-tool routing records
8,000 + 8,000 = 16,000 total records
```

This is why the report can correctly say both "500 tasks" and "16,000 records." The 500 tasks are the unique examples; the 16,000 records are all condition-by-setting evaluations of those tasks.

The run includes the reviewer-critical condition ladder:

- raw schema/doc baselines,
- schema and example baselines,
- prompt-only baselines,
- generated skill baselines,
- validation, repair, and gating baselines,
- documentation-heavy baselines,
- ReliaSkill v1.

## Story Across Pilot And Full Run

Before the full run, we ran a targeted proof-margin pilot with 40 tools, 200 tasks, and 6 critical conditions. That pilot answered a narrow question: after the method upgrade, does ReliaSkill v1 beat the strongest documentation-heavy baselines by more than a tiny margin?

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

## How The Current Pipeline Works

The key idea is simple:

> ReliaSkill does not merely show the model better tool documentation. It turns each tool into an executable contract, then only accepts calls that can satisfy that contract.

This matters because tool-use errors are often not caused by missing text. They are caused by weak enforcement. A model may read the right docs and still call the wrong tool, invent missing arguments, ignore side effects, or output schema-invalid JSON. ReliaSkill adds a reliability layer that checks these decisions before accepting them.

### 1. Tool Information Becomes A Contract

Each tool starts with schema and documentation:

- tool name,
- purpose,
- required arguments,
- optional arguments,
- types, enums, formats, and constraints,
- examples and generated skill descriptions.

ReliaSkill compiles this into a contract. In plain language, the contract says:

- what action this tool supports,
- when this tool should not be used,
- which arguments must be present,
- which argument values are allowed,
- which values must be grounded in the request,
- which repairs are safe,
- when the system must abstain.

For example, a money-transfer tool should not be used for a read-only balance request. A search tool should not be used when the user already gives a known path. A destructive tool should not be called when the user only asks for an explanation.

### 2. The Contract Policy Is Calibrated From Dev Controls

ReliaSkill v1 is not only a fixed rule list. It calibrates part of the contract policy using development controls.

The package builder uses:

- positive development examples,
- explicit development negatives,
- contrastive examples from nearby tools,
- counterfactual negatives,
- examples embedded in the generated skill artifact.

This gives the method a learned sense of which contract features matter for a tool. For instance, two banking tools may share many words, but one is read-only and one performs a transfer. ReliaSkill learns that shared topic words are not enough; action intent and grounded required fields matter.

The method also learns argument aliases from development examples. If users refer to `account_id` as "account number" or "from account," the runtime can bind that phrase to the right slot.

### 3. Runtime First Tries A Contract Decoder

At inference time, ReliaSkill first checks whether the request can be decided by the contract before relying on model generation.

There are two major paths:

- If the request clearly violates the tool boundary, ReliaSkill abstains.
- If the request clearly matches the tool and all required arguments are grounded, ReliaSkill can directly construct the tool call.

This helps small local models a lot. Many Qwen2.5-1.5B failures are not hard semantic failures. They are reliability failures:

- calling a similar but wrong tool,
- failing to abstain on negative controls,
- inventing missing values,
- outputting unsupported fields,
- ignoring read/write or destructive-action boundaries.

The contract decoder prevents many of these before the model produces a fragile JSON response.

### 4. Model Outputs Are Verified, Repaired, Or Blocked

If the contract decoder cannot decide, the model still produces a JSON tool-call decision. ReliaSkill then verifies it.

The verifier can:

- remove unsupported fields,
- safely coerce scalar values,
- canonicalize enum values,
- prune ungrounded optional values,
- fill required arguments only from grounded evidence,
- reject missing required arguments,
- reject schema violations,
- reject action-intent conflicts,
- reject side-effect conflicts,
- abstain when ambiguity is safer.

So model output is not accepted just because it is syntactically JSON. It must satisfy the contract.

### 5. Routing Uses The Same Proof Logic

Hidden-tool routing improves because ReliaSkill applies the same proof idea to candidate tools.

Raw documentation often makes similar tools look relevant. ReliaSkill asks a sharper question:

> Which candidate can prove that this request satisfies its contract?

This helps with near-miss tools. For example:

- A request mentions "transactions."
- Multiple banking tools mention "transactions" or "accounts."
- A transfer tool may be topically related.
- But if the request asks to search transactions, the transfer tool fails action-intent and required-field checks.

This is why routing improves alongside argument correctness.

## Why ReliaSkill Wins By So Much

The full run confirms the pilot story: more documentation is not enough. The strongest docs baseline, `raw_docs_full`, is better than many prompt/skill baselines, but it remains near 0.39 joint exact match. ReliaSkill v1 reaches 0.892 structured and 0.880 routing.

The large gain is plausible because the benchmark stresses exactly the failures that contracts are designed to catch:

- adjacent wrong-tool requests,
- missing required information,
- ambiguous requests where abstention is safer,
- read/write and destructive/read-only mismatches,
- schema-invalid arguments,
- argument values not grounded in the user request,
- distractor tools in hidden-tool routing.

ReliaSkill improves three things at once:

1. Tool selection.
   It rejects tools that are topically similar but contract-invalid.

2. Abstention.
   It refuses calls when required information, action intent, or side-effect authorization is missing.

3. Argument correctness.
   It grounds required fields and verifies schema compliance before accepting the call.

This explains the verifier action rates:

- Structured-call verifier action rate: 0.906
- Hidden-tool routing verifier action rate: 0.592

The reliability layer is actively changing outputs. It is not just adding explanatory metadata after the fact.

## What This Result Supports

This full run supports the following claims for the Qwen2.5-1.5B setting:

- ReliaSkill v1 substantially outperforms raw MCP schema exposure.
- ReliaSkill v1 substantially outperforms full raw documentation exposure.
- ReliaSkill v1 substantially outperforms generated skill, validation, repair, and gating baselines.
- The gains hold in both structured-call and hidden-tool routing settings.
- The gains are statistically supported by paired tests.
- The run is claim-ready under the current readiness audit.

The strongest concise result is:

> On the full 100-tool, 500-task Qwen2.5-1.5B run, ReliaSkill v1 improves joint exact match from 0.390 to 0.892 over the strongest documentation baseline in structured calls, and from 0.388 to 0.880 in hidden-tool routing.

## Remaining Caveats

This is a strong single-model result, but it is not the entire paper story yet.

Remaining work:

- Multi-model replication would strengthen generality.
- External benchmark replication would strengthen dataset breadth.
- Live/sandbox execution would strengthen end-to-end operational realism.
- Ablation-specific reporting should be used to show which ReliaSkill components drive the gain.

However, the current result is already much stronger than the earlier small-margin result. The central concern is no longer whether ReliaSkill beats the strongest baseline on this benchmark. It does, by a large margin. The next concern is how broadly that gain replicates.

## Recommended Next Steps

1. Freeze and preserve the full-run archive.
   The full result archive is already saved in `outputs/frozen_results`.

2. Update the paper result tables and figures.
   Use the full-run numbers as the main Qwen2.5-1.5B result.

3. Run a smaller multi-model replication.
   A focused 5 or 6 condition comparison across another model family may be more valuable than another full Qwen rerun.

4. Prepare reviewer-facing ablations.
   The report should explain that ReliaSkill's gain comes from executable contracts, dev-calibrated policy, runtime verification, grounded argument completion, and contract routing.

5. Keep the pilot in the narrative.
   The pilot is useful because it shows the decision process: first a targeted proof-margin check, then a full claim-ready run that preserves the large margin.
