from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.analysis.proof_ledger import (  # noqa: E402
    audit_runtime_invariants,
    extract_proof_ledger_cases,
    write_invariant_report,
    write_proof_ledger_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract ReliaSkill proof-ledger cases and audit runtime invariants.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--condition", default="reliaskill_v1")
    parser.add_argument("--max-cases-per-type", type=int, default=2)
    parser.add_argument("--no-routing", action="store_true")
    parser.add_argument("--output-json", type=Path, default=Path("outputs/reports/reliaskill_proof_ledger.json"))
    parser.add_argument("--output-md", type=Path, default=Path("outputs/reports/reliaskill_proof_ledger.md"))
    parser.add_argument("--invariant-json", type=Path, default=Path("outputs/reports/reliaskill_runtime_invariants.json"))
    parser.add_argument("--invariant-md", type=Path, default=Path("outputs/reports/reliaskill_runtime_invariants.md"))
    args = parser.parse_args()

    include_routing = not args.no_routing
    ledger = extract_proof_ledger_cases(
        args.run_dir,
        condition=args.condition,
        max_cases_per_type=args.max_cases_per_type,
        include_routing=include_routing,
    )
    invariants = audit_runtime_invariants(args.run_dir, condition=args.condition, include_routing=include_routing)
    ledger_paths = write_proof_ledger_report(ledger, output_json=args.output_json, output_md=args.output_md)
    invariant_paths = write_invariant_report(invariants, output_json=args.invariant_json, output_md=args.invariant_md)
    print(
        json.dumps(
            {
                "cases": len(ledger["cases"]),
                "case_counts": ledger["case_counts"],
                "invariants_ok": invariants["ok"],
                "violations": invariants["num_violations"],
            },
            sort_keys=True,
        )
    )
    print(f"ledger_json={ledger_paths['json']}")
    print(f"ledger_markdown={ledger_paths['markdown']}")
    print(f"invariant_json={invariant_paths['json']}")
    print(f"invariant_markdown={invariant_paths['markdown']}")


if __name__ == "__main__":
    main()
