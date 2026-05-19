from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reliaskill.analysis.preregistration import (  # noqa: E402
    audit_preregistered_success,
    write_preregistration_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit preregistered ReliaSkill success criteria against result tables.")
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--tables-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, default=Path("outputs/reports/preregistered_success_audit.json"))
    parser.add_argument("--output-md", type=Path, default=Path("outputs/reports/preregistered_success_audit.md"))
    args = parser.parse_args()

    report = audit_preregistered_success(preregistration_path=args.preregistration, tables_dir=args.tables_dir)
    paths = write_preregistration_report(report, output_json=args.output_json, output_md=args.output_md)
    print(json.dumps({"ok": report["ok"], "failures": report["num_failures"], "warnings": report["num_warnings"]}, sort_keys=True))
    print(f"json={paths['json']}")
    print(f"markdown={paths['markdown']}")


if __name__ == "__main__":
    main()
