# ReliaSkill v1 Proof-Margin Pilot Report

## Summary

We ran a targeted Qwen2.5-1.5B pilot after the ReliaSkill v1 method upgrade. The goal was to test whether the upgraded method can beat the strongest documentation-heavy baselines by a meaningful margin before spending GPU time on the full claim-ready rerun.

The pilot result is very strong: ReliaSkill v1 improves joint exact match by more than 52 points over the strongest baseline in both structured-call and hidden-tool routing settings.

## Pilot Setup

- Local artifact archive: `outputs/overnight_qwen15b_4gpu_reliaskill_v1_proof_margin_pilot_fast/reliaskill_v1_proof_margin_pilot_fast_results_20260520_071724.tar.gz`
- Local extracted artifacts: `outputs/overnight_qwen15b_4gpu_reliaskill_v1_proof_margin_pilot_fast`
- Config: `configs/experiments/overnight_qwen15b_4gpu_reliaskill_v1_proof_margin_pilot_fast.yaml`
- Output root: `outputs/overnight_qwen15b_4gpu_reliaskill_v1_proof_margin_pilot_fast`
- Model: `Qwen/Qwen2.5-1.5B-Instruct`, 4-bit local HF
- Tools: 40
- Tasks: 200
- Conditions: 6 targeted conditions
- Total saved records: 2,400
- Routing enabled: yes
- Live execution: disabled
- Backend fallbacks: none
- Dataset integrity: passed

This report was verified against the extracted local CSV/JSON/Markdown artifacts, including `main_results.csv`, `routing_results.csv`, `stat_tests.csv`, `routing_stat_tests.csv`, and `reliaskill_readiness_pilot.md`.

The readiness audit has one expected pilot-only failure: the pilot config intentionally omitted several reviewer-critical full-run baselines. All result, statistical, routing, slice, no-fallback, and runtime-verifier checks passed.

## Main Results

Structured-call benchmark:

| Condition | Joint Exact Match | Tool Selection | Argument Exact |
|---|---:|---:|---:|
| ReliaSkill v1 | 0.915 | 0.960 | 0.945 |
| raw_docs_full | 0.380 | 0.395 | 0.425 |
| raw_mcp | 0.375 | 0.375 | 0.420 |
| generated_skill_base | 0.360 | 0.360 | 0.405 |
| skill_prompt_verbose_docs | 0.355 | 0.365 | 0.400 |
| gated_skill | 0.355 | 0.355 | 0.400 |

Hidden-tool routing:

| Condition | Joint Exact Match | Tool Selection | Argument Exact |
|---|---:|---:|---:|
| ReliaSkill v1 | 0.905 | 0.950 | 0.950 |
| raw_docs_full | 0.380 | 0.395 | 0.425 |
| raw_mcp | 0.370 | 0.370 | 0.415 |
| generated_skill_base | 0.360 | 0.360 | 0.405 |
| skill_prompt_verbose_docs | 0.355 | 0.360 | 0.400 |
| gated_skill | 0.355 | 0.355 | 0.400 |

## Statistical Tests

ReliaSkill v1 significantly beats the strongest baseline, `raw_docs_full`.

Structured-call benchmark:

- `raw_docs_full` vs `reliaskill_v1`: +0.535 joint exact match
- Approximate randomization: `p = 0.001996`
- McNemar: `p = 0.0` as reported in the generated table

Hidden-tool routing:

- `raw_docs_full` vs `reliaskill_v1`: +0.525 joint exact match
- Approximate randomization: `p = 0.001996`
- McNemar: `p = 0.0` as reported in the generated table

ReliaSkill v1 also significantly beats `raw_mcp`, `generated_skill_base`, `skill_prompt_verbose_docs`, and `gated_skill`.

## Method Interpretation

The large margin suggests that the upgraded ReliaSkill v1 path is no longer merely adding documentation or prompt wording. It is acting as an executable reliability layer: dev-calibrated contract policy, runtime schema-contract verification, action gating, and grounded argument extraction substantially improve both routing and argument correctness.

The verifier action rate is high:

- Structured-call benchmark: 0.985
- Hidden-tool routing: 0.605

This indicates that the reliability machinery is actively changing model behavior rather than passively annotating outputs.

## How The Current Pipeline Works

The simplest way to describe the current ReliaSkill v1 pipeline is:

> ReliaSkill turns each tool description into an executable contract, then requires every predicted tool call to pass that contract before it is accepted.

Most baselines expose information to the model and ask the model to decide. For example, `raw_docs_full` gives the model much more documentation, while `generated_skill_base` gives a compact generated skill description. These baselines can help, but the downstream model still has to infer on its own whether the request really matches the tool, whether all required inputs are present, and whether the JSON arguments are valid.

ReliaSkill v1 changes the problem. Instead of relying only on the model's free-form interpretation, it builds a structured reliability layer around the model.

### 1. Tool Information Becomes A Contract

For each tool, ReliaSkill compiles a contract from the schema, generated skill artifact, documentation evidence, and development controls. In plain language, the contract says:

- when this tool is allowed to be used,
- when this tool must not be used,
- which arguments are required,
- what types and formats those arguments must satisfy,
- which values must be explicitly grounded in the user request or authorized context,
- which repairs are safe,
- which failures require abstention.

So a tool is not represented only as text like "this tool transfers money." It is represented as a set of obligations:

- Is the user actually asking to transfer money?
- Are source account, destination account, and amount present?
- Is this a read-only banking request instead?
- Is the model inventing any field?
- Is this an adjacent request for a different banking tool?

Only calls that satisfy these obligations are allowed through.

### 2. The Contract Policy Is Calibrated On Dev Controls

The current method is not just a hand-written rules system. ReliaSkill learns/calibrates part of the contract policy from development controls.

For each tool, the package builder uses:

- positive development examples,
- explicit negative examples,
- contrastive examples from nearby tools,
- counterfactual negatives,
- examples embedded in the generated skill artifact.

This teaches the contract which features usually distinguish a correct call from a near miss. For example, two tools may both mention "bank account," but one is for reading balances and another is for transferring money. The calibrated policy learns that shared topical words are not enough; action intent and required grounded fields matter.

The package also learns simple slot-grounding aliases from development examples. If examples show that users refer to `account_id` as "account number," "from account," or "account," ReliaSkill can extract the right value more reliably at runtime.

### 3. Runtime First Tries A Contract Decoder

At prediction time, ReliaSkill v1 first checks whether the request can be handled directly by the executable contract.

There are two important cases:

- If the request clearly violates the tool boundary, ReliaSkill abstains before calling the model.
- If the request clearly matches the tool and all required arguments can be grounded, ReliaSkill can construct the call directly.

This is especially important for small local models. Many failures are not deep reasoning failures; they are reliability failures:

- calling a tool on an adjacent negative request,
- using a similar but wrong tool,
- inventing a missing argument,
- outputting unsupported fields,
- choosing a value that does not satisfy the schema,
- failing to abstain on ambiguity.

The contract decoder prevents many of these failures before the model can produce a fragile JSON answer.

### 4. If The Model Produces JSON, The Runtime Verifier Audits It

When the contract decoder cannot confidently decide, the downstream model still predicts a JSON tool decision. ReliaSkill then verifies that prediction.

The verifier checks the model output against the compiled contract. It can:

- remove unsupported fields,
- coerce safe scalar values,
- canonicalize enum values,
- prune optional arguments that are not grounded,
- fill required arguments only when grounded evidence exists,
- reject calls with missing required fields,
- reject calls with action or side-effect conflicts,
- abstain when the request is ambiguous or belongs to a nearby tool.

This means invalid model outputs are not automatically accepted. They are either safely repaired or converted into a scored abstention.

### 5. Routing Uses The Same Proof Logic

The hidden-tool routing benchmark is harder because the system has to select the correct tool from a candidate set. Similar tools often share many words, so documentation alone can be misleading.

ReliaSkill uses the same contract logic for routing. It asks which candidate tool can actually prove that the request satisfies its contract.

For example:

- A request to "search transactions" may mention banking terms.
- A transfer tool may also mention banking terms.
- Raw docs can make both look relevant.
- ReliaSkill rejects the transfer tool because the request does not ask for a transfer and does not provide transfer-specific required fields.

This is why routing improves together with structured tool-call prediction. ReliaSkill is not only formatting better arguments; it is changing which tool is considered valid.

## Why The Pilot Margin Is Plausible

The pilot margin is large, so it is worth explaining why it is plausible rather than treating it as magic.

The benchmark contains many examples where a model must either call the exact right tool or abstain on a near miss. These are precisely the cases where ordinary documentation baselines struggle.

`raw_docs_full` gives the model more information, but it does not enforce the decision. The model can still:

- over-match broad keywords,
- call a tool on a similar but wrong intent,
- hallucinate missing required fields,
- ignore schema constraints,
- fail to distinguish read-only and write-like actions,
- produce a JSON object that looks plausible but violates the tool contract.

ReliaSkill directly targets those failure modes.

In this pilot, `reliaskill_v1` improved over the strongest baseline, `raw_docs_full`, by:

- +0.535 joint exact match in the structured-call benchmark,
- +0.525 joint exact match in hidden-tool routing.

The improvement comes from three interacting effects:

1. Better abstention on negative and ambiguous requests.
   ReliaSkill is stricter about not using a tool unless the request satisfies the tool contract.

2. Better tool selection among similar tools.
   Contract routing rejects candidates that are topically similar but fail action intent, required-field, or side-effect checks.

3. Better argument correctness.
   Grounded extraction and runtime schema verification reduce missing, invented, malformed, or unsupported arguments.

This also explains why verbose documentation alone is not enough. Documentation increases what the model can read. ReliaSkill changes what the system is allowed to accept.

## What The Pilot Does And Does Not Prove

This pilot is strong evidence that the upgraded method path is working, but it is not yet the final paper claim.

It does show:

- large gains over the strongest documentation-heavy baseline in a clean 40-tool, 200-task pilot,
- statistically significant paired wins,
- separate wins in structured-call and hidden-tool routing settings,
- no backend fallbacks in accepted outputs,
- dataset integrity checks passed,
- runtime verifier evidence present in the artifacts.

It does not yet show:

- the full 100-tool, 500-task result,
- the complete 16-condition reviewer-critical baseline ladder,
- whether the same large margin holds at full scale,
- whether the effect generalizes across multiple model families.

Because the pilot margin is unusually large, the full run should be interpreted carefully. The most important next checks are dataset integrity, full baseline coverage, no-fallback evidence, and whether the `raw_docs_full` margin remains large in the clean full run.

## Caveats

This is a targeted pilot, not the final claim-ready experiment.

- It uses 40 tools and 200 tasks, not the full 100-tool/500-task setting.
- It includes 6 targeted conditions, not the full reviewer-critical condition ladder.
- The effect size is large enough that the full run must carefully preserve dataset-integrity checks, no-fallback checks, and full baseline coverage.

## Recommended Next Step

Run the clean full proof-margin config:

`configs/experiments/overnight_qwen15b_4gpu_reliaskill_v1_proof_margin.yaml`

This expands to 100 tools, 500 tasks, and 16 conditions, while keeping the same upgraded ReliaSkill v1 method path and clean output root.

If the full run preserves even a substantial fraction of the pilot margin, this becomes a strong EMNLP-level result: large effect size, significant paired tests, hidden-tool routing wins, and clear evidence that reliability contracts improve agent tool use beyond raw docs and prompt baselines.
