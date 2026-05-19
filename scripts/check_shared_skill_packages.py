from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.config import load_json_config
from autoskill.conditions import (
    LEGACY_RELIASKILL_CHALLENGER,
    RELIASKILL_CHALLENGER,
    RELIASKILL_V1_CONTRACT_ABLATIONS,
    normalize_condition_names,
)
from autoskill.experiment import load_tools
from reliaskill.cluster import _configured_live_tools, selected_tool_names, shared_package_root, tool_slug

PACKAGE_BACKED_CONDITIONS = {
    "generated_skill_base",
    "validated_skill",
    "repaired_skill",
    "gated_skill",
    RELIASKILL_CHALLENGER,
    LEGACY_RELIASKILL_CHALLENGER,
    "multi_candidate_skill_k3_behavior_select",
    "multi_candidate_repaired_gated",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check shared ReliaSkill package coverage before a strict run.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--shared-packages", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_json_config(args.config)
    all_tools = load_tools(config["tools_path"])
    benchmark_names = selected_tool_names(config, all_tools)
    tools = {name: all_tools[name] for name in benchmark_names}
    tools.update(_configured_live_tools(config))
    package_root = args.shared_packages or shared_package_root(config, args.output_root)
    configured_conditions = normalize_condition_names([str(item) for item in config.get("conditions") or []]) or []
    conditions = ["generated_skill_base"]
    conditions.extend(
        condition
        for condition in configured_conditions
        if condition in PACKAGE_BACKED_CONDITIONS and condition != "generated_skill_base"
    )
    if (
        any(condition in RELIASKILL_V1_CONTRACT_ABLATIONS for condition in configured_conditions)
        and RELIASKILL_CHALLENGER not in conditions
    ):
        conditions.append(RELIASKILL_CHALLENGER)
    missing = []
    for tool_name in sorted(tools):
        for condition in conditions:
            path = package_root / tool_slug(tool_name) / tool_slug(condition) / "skill.json"
            if not path.exists():
                missing.append({"tool_name": tool_name, "condition": condition, "path": str(path)})
    report = {
        "valid": not missing,
        "config_path": str(args.config),
        "shared_package_root": str(package_root),
        "num_tools": len(tools),
        "num_conditions": len(conditions),
        "expected_packages": len(tools) * len(conditions),
        "missing_packages": len(missing),
        "missing": missing[:200],
    }
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"valid={str(report['valid']).lower()}")
        print(f"shared_package_root={report['shared_package_root']}")
        print(f"expected_packages={report['expected_packages']}")
        print(f"missing_packages={report['missing_packages']}")
        for row in missing[:20]:
            print(f"missing {row['tool_name']} {row['condition']} {row['path']}")
    if missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
