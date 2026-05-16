from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autoskill.variant_selection import (
    DEFAULT_POLICY,
    VariantSelectionPolicy,
    apply_selection_manifest,
    load_dev_evidence,
    select_method_variant,
    write_selection_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select an existing ReliaSkill method variant using dev-only structured-call and routing evidence."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    select = subparsers.add_parser("select", help="Write a dev-only variant selection manifest.")
    select.add_argument("--prediction-records", nargs="*", default=[], type=Path, help="Dev-only prediction_records.jsonl files.")
    select.add_argument("--routing-records", nargs="*", default=[], type=Path, help="Dev-only routing_records.jsonl files.")
    select.add_argument("--candidates", nargs="*", default=None, help="Existing condition names eligible for selection.")
    select.add_argument("--selection-id", default=None, help="Stable identifier to store in the manifest.")
    select.add_argument("--output-manifest", required=True, type=Path, help="New JSON manifest path.")
    select.add_argument("--harm-penalty", type=float, default=DEFAULT_POLICY.harm_penalty)

    apply = subparsers.add_parser("apply", help="Copy the selected package variant into a new package root.")
    apply.add_argument("--manifest", required=True, type=Path, help="Selection manifest JSON.")
    apply.add_argument("--source-package-root", required=True, type=Path, help="Root containing existing packages.")
    apply.add_argument("--output-package-root", required=True, type=Path, help="New package root to create.")
    apply.add_argument("--target-condition", default=None, help="Optional condition directory name in the copied packages.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "select":
        policy = VariantSelectionPolicy(harm_penalty=args.harm_penalty)
        records, inputs = load_dev_evidence(
            prediction_record_paths=args.prediction_records,
            routing_record_paths=args.routing_records,
        )
        manifest = select_method_variant(
            records,
            candidates=args.candidates,
            policy=policy,
            selection_id=args.selection_id,
            inputs=inputs,
        )
        path = write_selection_manifest(manifest, args.output_manifest)
        print(
            json.dumps(
                {
                    "manifest": str(path),
                    "selected_condition": manifest["selected_condition"],
                    "selected_score": manifest["selected_score"],
                    "candidate_count": len(manifest["candidates"]),
                },
                indent=2,
            )
        )
        return

    if args.command == "apply":
        applied = apply_selection_manifest(
            manifest_path=args.manifest,
            source_package_root=args.source_package_root,
            output_package_root=args.output_package_root,
            target_condition=args.target_condition,
        )
        print(
            json.dumps(
                {
                    "output_package_root": applied["output_package_root"],
                    "target_condition": applied["target_condition"],
                    "copied_packages": len(applied["copied_packages"]),
                },
                indent=2,
            )
        )
        return

    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
