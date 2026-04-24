# ReliaSkill Low-Compute Experimental Story

The revised paper should explicitly frame ReliaSkill as a low-compute reliability method. The system does not rely on trajectory pools, lifelong memory accumulation, multi-agent co-evolution, or full executable skill-package search. The intended claim is narrower and stronger: deterministic validation, behavior-grounded negative controls, targeted repair, and deployment gating can make compact MCP skill artifacts safer and more useful before an agent sees them.

## Paper Updates To Make

Add this story in these places:

1. **Abstract / Introduction**: state that the method is designed for cold-start MCP settings with limited compute and sparse documentation. Mention that core verification is deterministic and that repair is section-level rather than full skill regeneration.
2. **Method**: add a paragraph after the pipeline overview explaining that validation, scoring, and gating are intentionally rule-based in the first version. This is a design choice for reproducibility and low compute, not a limitation hidden in implementation.
3. **Experimental Setup**: report the hardware budget: one workstation-class setup with RTX A5000 / RTX 5070 Ti-class GPUs. Say experiments use small local instruction models first, with larger local models only as optional baselines.
4. **Baselines**: include “smaller model + reliable/gated skill” versus “larger model + raw MCP schema” as a main comparison. This directly tests whether verifier-backed skill artifacts can substitute for scaling the downstream model.
5. **Limitations**: say that the current benchmark emphasizes pre-deployment skill reliability and tool-call structure, not full live MCP server execution. Larger server-execution studies such as MCP-Atlas are complementary.

Suggested wording:

> ReliaSkill is designed for low-compute MCP cold-start settings: it avoids trajectory-pool distillation, expensive co-evolution, and full executable skill search. Instead, it uses deterministic structural checks, behavior-grounded negative controls, targeted section-level repair, and simple deployment gating to improve compact skill artifacts before agent deployment.

## Runnable Setup

Preflight the low-compute comparison:

```powershell
python scripts\run_model_comparison.py --config configs\model_comparison.low_compute.sample.json --preflight-only
```

Run the comparison:

```powershell
python scripts\run_model_comparison.py --config configs\model_comparison.low_compute.sample.json
```

The sample config compares:

- `small_3b_reliable_skill`: Qwen2.5-3B predictor with `gated_skill`.
- `larger_7b_raw_mcp`: Qwen2.5-7B predictor with `raw_mcp`.

Use 3B vs 7B as the default A5000 / 5070 Ti-safe setting. Treat 14B 4-bit as optional if memory permits, not as the default result needed for the paper.

## Outputs

The comparison runner writes:

- `outputs/model_comparison_low_compute/model_comparison_manifest.json`
- `outputs/model_comparison_low_compute/model_comparison_summary.json`
- `outputs/model_comparison_low_compute/model_comparison_report.md`
- `outputs/model_comparison_low_compute/model_comparison_summary.csv`

Each underlying run also writes the full reliability pipeline outputs, including per-tool packages, validation reports, behavior reports, repair reports, and reliability scores.
