from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.analysis.public_claims import (
    apply_public_claim_fixes,
    scan_public_claims,
    write_public_claim_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check public ReliaSkill text for stale result counts and overclaims.")
    parser.add_argument("--paths", nargs="+", required=True, help="Files or directories to scan.")
    parser.add_argument("--output-json", default="outputs/public_claims_audit.json")
    parser.add_argument("--output-md", default="outputs/public_claims_audit.md")
    parser.add_argument("--fix", action="store_true", help="Apply conservative README.md wording/count fixes before scanning.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fix_summary = None
    if args.fix:
        fix_summary = apply_public_claim_fixes(args.paths)
        for warning in fix_summary["warnings"]:
            print(f"warning: {warning}", file=sys.stderr)

    audit = scan_public_claims(
        args.paths,
        exclude_paths=[args.output_json, args.output_md],
    )
    if fix_summary is not None:
        audit["fix_summary"] = fix_summary
        audit["warnings"] = [*fix_summary["warnings"], *audit["warnings"]]

    paths = write_public_claim_outputs(
        audit,
        output_json=args.output_json,
        output_md=args.output_md,
    )

    for warning in audit["warnings"]:
        print(f"warning: {warning}", file=sys.stderr)
    print(f"scanned_files={audit['scanned_files']}")
    print(f"issues={audit['issue_count']}")
    print(f"summary_json={paths['json']}")
    print(f"summary_md={paths['markdown']}")
    return 1 if audit["issue_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
