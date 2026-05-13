# ReliaSkill MCP Cold-Start Reliability Architecture

> Maintainer note: this is an archival architecture note from an earlier experiment buildout. It is retained for design context, but the README is the canonical public summary of the reported evaluation.

ReliaSkill targets reliable MCP skill construction before deployment. The unit of study is a compact skill artifact generated from raw MCP schema/docs under cold-start constraints, then validated, behavior-tested, repaired, scored, and gated.

## Pipeline

1. **Ingest and normalize** raw MCP definitions into `ToolIR`, including schema complexity, documentation completeness, ambiguity flags, provenance, side-effect hints, and safety hints.
2. **Construct compact skills** for earlier internal variants such as `docs_only`, `naive_skill`, `validated_skill`, `repaired_skill`, and `gated_skill`, alongside historical baselines.
3. **Validate deterministically** with structured reports that identify failing section, repairability, and evidence.
4. **Test behavior** on positive controls and adjacent negative controls to measure trigger precision, trigger recall, exact match, argument validity, and harmful skill injection.
5. **Repair targeted sections** rather than regenerating the whole artifact, including narrow negative-control boundaries when a skill over-triggers.
6. **Score and gate** using rule-based reliability features and deploy/repair/reject decisions.

## Main Command

```powershell
python scripts\run_reliability_pipeline.py --config configs\experiment.reliability.heuristic.sample.json
```

The default fixture uses `data/eval/public_mcp_filesystem_reliability.jsonl`, which adds negative controls for adjacent file-system tasks. This is intentionally small but pins down the revised evaluation protocol.

Run-level summaries are written to:

- `outputs/reliability_heuristic_sample/reliability_manifest.json`
- `outputs/reliability_heuristic_sample/reliability_records.jsonl`
- `outputs/reliability_heuristic_sample/reports/reliability_report.md`
- `outputs/reliability_heuristic_sample/reports/reliability_summary.csv`

## Runnable Conditions

- `raw_mcp`: original schema/docs exposure.
- `schema_only`: deterministic schema rendering.
- `docs_only`: sparse docs-only control.
- `naive_skill`: one-shot generated artifact.
- `validated_skill`: generated artifact with structural validation report.
- `repaired_skill`: validated artifact after conservative repair.
- `gated_skill`: repaired artifact with reliability score and deployment decision.

## Current Limits

- Reliability scoring is rule-based, not learned/calibrated.
- Negative controls are currently a minimal filesystem fixture.
- BFCL-derived routing data is useful for distractor/routing experiments, but its empty or weak schemas should not be used as the main evidence for rich MCP argument construction.
