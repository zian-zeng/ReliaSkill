# ReliaSkill v1 Contract Formalism

ReliaSkill v1 treats a generated skill as an executable contract rather than free-form documentation.

For each tool `t`, ReliaSkill compiles a contract:

```text
C_t = <I_t, S_t, G_t, E_t, R_t, A_t, P_t>
```

- `I_t`: intent/action families supported by the tool.
- `S_t`: schema obligations over allowed fields, required fields, nested paths, types, enums, formats, and array bounds.
- `G_t`: grounding obligations that required arguments must be supported by the user request or authorized context.
- `E_t`: effect obligations describing read/write/delete/send/compute side effects.
- `R_t`: repair-preserving transformations, such as nested-field lifting, safe scalar coercion, enum canonicalization, required-value replacement from grounded evidence, and optional pruning.
- `A_t`: abstention obligations for missing inputs, action conflicts, schema violations, ambiguity, and planning-only requests.
- `P_t`: calibrated policy over contract features, with hard blockers for missing required inputs, action conflicts, and schema violations.

A tool call is accepted only if the contract evaluator can produce a proof ledger showing that required obligations are satisfied or safely repaired. Routing uses the same contract evaluator to rank and gate candidate tools; runtime verification records before/after proof ledgers and actionable failure reports.

## Proof Obligations

The current implementation exposes these obligations:

- `intent_supported_or_nonconflicting`
- `side_effect_allowed_by_request`
- `all_required_arguments_grounded`
- `arguments_schema_valid`
- `optional_arguments_grounded_or_pruned`
- `ambiguity_resolved_or_abstained`
- `multi_step_dependencies_bound_or_unresolved`
- `execution_feedback_repaired_or_aborted`
- `adaptive_policy_acceptance`

## Grounding Sources

Grounding is source-aware. The current request is always used for action intent. Required argument values may also be grounded from:

- conversation history,
- artifact context,
- previous tool observations.

This deliberately separates current intent from non-local evidence so stale context cannot authorize a conflicting action.

## Contract-Preserving Operations

Repairs are only allowed when they preserve the contract:

- Unsupported fields are removed.
- Optional values are kept only when grounded.
- Invalid required values can be replaced only by grounded alternatives.
- Required values can be filled only from request/context evidence.
- Action or side-effect conflicts cause abstention unless explicitly disabled in an ablation condition.

## Component Ablations

The reviewer-facing ablation config `configs/experiments/reliaskill_v1_contract_ablation.yaml` isolates:

- no contract routing,
- no runtime grounding,
- no action gate,
- no schema repair,
- no ambiguity abstention,
- no contextual grounding.

The readiness audit checks that the full method beats any reported ReliaSkill v1 ablation when ablation rows are present.
