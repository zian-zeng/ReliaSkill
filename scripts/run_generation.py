from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.multi_candidate import load_multi_candidate_config, run_multi_candidate_pipeline
from autoskill.prompt_templates import generate_prompt_template_skills
from autoskill.multi_candidate import load_tools_as_toolir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and select multi-candidate ReliaSkill artifacts.")
    parser.add_argument("--config", type=Path, default=Path("configs/skills/multi_candidate.yaml"), help="Multi-candidate generation YAML config.")
    parser.add_argument("--limit", type=int, default=None, help="Optional smoke-test limit for number of tools.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Override output directory.")
    parser.add_argument("--candidate-k", type=int, default=None, help="Override candidate count K.")
    parser.add_argument("--selection-policy", default=None, help="Override selection policy.")
    parser.add_argument("--compactness-variants", action="store_true", help="Also generate compactness variant artifacts and stats.")
    parser.add_argument("--prompt-templates", action="store_true", help="Generate prompt-template ablation skill artifacts from config.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_multi_candidate_config(args.config)
    if args.limit is not None:
        config["max_tools"] = args.limit
    if args.output_dir is not None:
        config["output_dir"] = str(args.output_dir)
    if args.candidate_k is not None:
        config["candidate_k"] = args.candidate_k
    if args.selection_policy is not None:
        config["selection_policy"] = args.selection_policy
    if args.compactness_variants:
        compactness = dict(config.get("compactness_variants") or {})
        compactness["enabled"] = True
        config["compactness_variants"] = compactness
    prompt_templates = dict(config.get("prompt_templates") or {})
    if args.prompt_templates:
        prompt_templates["enabled"] = True
        config["prompt_templates"] = prompt_templates
    if prompt_templates.get("enabled"):
        tools = load_tools_as_toolir(config["tools_path"], limit=config.get("max_tools") if isinstance(config.get("max_tools"), int) else None)
        template_ids = list(prompt_templates.get("template_ids") or [])
        dev_controls = _load_jsonl(config.get("dev_controls_path")) if prompt_templates.get("include_dev_controls") else []
        records = generate_prompt_template_skills(
            tools,
            template_ids=template_ids,
            output_root=prompt_templates.get("output_root", "generated_skills"),
            stats_path=prompt_templates.get("stats_path", "outputs/tables/prompt_template_generation_stats.csv"),
            dev_controls=dev_controls,
        )
        print(f"tools={len(tools)}")
        print(f"prompt_templates={len(template_ids)}")
        print(f"generated_prompt_template_skills={len(records)}")
        print(f"prompt_template_output={prompt_templates.get('output_root', 'generated_skills')}")
        print(f"prompt_template_stats={prompt_templates.get('stats_path', 'outputs/tables/prompt_template_generation_stats.csv')}")
        return
    records = run_multi_candidate_pipeline(config)
    print(f"tools={len(records)}")
    print(f"candidate_k={config['candidate_k']}")
    print(f"selection_policy={config['selection_policy']}")
    print(f"output_dir={config['output_dir']}")
    print(f"candidate_scores={Path(str(config['output_dir'])) / 'candidate_scores.jsonl'}")
    compactness = config.get("compactness_variants") or {}
    if compactness.get("enabled"):
        print(f"compactness_stats={compactness.get('stats_path')}")


def _load_jsonl(path: object) -> list[dict]:
    if not path:
        return []
    input_path = Path(str(path))
    if not input_path.exists():
        return []
    records = []
    import json

    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    records.append(value)
    return records


if __name__ == "__main__":
    main()
