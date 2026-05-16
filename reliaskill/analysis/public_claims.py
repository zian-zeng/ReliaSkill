from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


ARCHIVAL_MARKERS = ("archival", "pre-dedup", "old run", "deprecated", "historical")

STALE_VALUE_SUGGESTION = (
    "Use post-dedup public counts (290 tools and 1,450 selected held-out controls) "
    "unless this is explicitly labeled archival, pre-dedup, deprecated, historical, or an old run."
)

TEXT_SUFFIXES = {
    "",
    ".bib",
    ".cfg",
    ".csv",
    ".html",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".rst",
    ".tex",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}

BINARY_SUFFIXES = {
    ".bmp",
    ".gif",
    ".gz",
    ".jpeg",
    ".jpg",
    ".parquet",
    ".pdf",
    ".pkl",
    ".png",
    ".pyc",
    ".svgz",
    ".zip",
}


@dataclass(frozen=True)
class ClaimIssue:
    path: str
    line_number: int
    matched_text: str
    issue_type: str
    suggestion: str


@dataclass(frozen=True)
class ClaimPattern:
    regex: re.Pattern[str]
    issue_type: str
    suggestion: str


STALE_VALUE_PATTERNS: tuple[ClaimPattern, ...] = (
    ClaimPattern(
        re.compile(r"(?<![\w.])0\s*/\s*2950(?!\w)"),
        "stale_final_result_value",
        STALE_VALUE_SUGGESTION,
    ),
    ClaimPattern(
        re.compile(r"(?<![\w.])2,950(?!\w)"),
        "stale_final_result_value",
        STALE_VALUE_SUGGESTION,
    ),
    ClaimPattern(
        re.compile(r"(?<![\w.])2950(?!\w)"),
        "stale_final_result_value",
        STALE_VALUE_SUGGESTION,
    ),
    ClaimPattern(
        re.compile(r"(?<![\w.])1,475(?!\w)"),
        "stale_final_result_value",
        STALE_VALUE_SUGGESTION,
    ),
    ClaimPattern(
        re.compile(r"(?<![\w.])1475(?!\w)"),
        "stale_final_result_value",
        STALE_VALUE_SUGGESTION,
    ),
    ClaimPattern(
        re.compile(r"(?<![\w.])295(?!\w)"),
        "stale_final_result_value",
        STALE_VALUE_SUGGESTION,
    ),
)

OVERCLAIM_PATTERNS: tuple[ClaimPattern, ...] = (
    ClaimPattern(
        re.compile(r"\brequires a governed representation layer\b", re.IGNORECASE),
        "overclaim_universal_necessity",
        "Replace universal 'requires' with 'can benefit substantially from' or 'our results provide evidence that'.",
    ),
    ClaimPattern(
        re.compile(r"\bsafe enough to expose\b", re.IGNORECASE),
        "overclaim_safety",
        "Use 'no observed harmful activation on held-out adjacent negatives' instead of broad safety language.",
    ),
    ClaimPattern(
        re.compile(r"\bproduction safety\b", re.IGNORECASE),
        "overclaim_safety",
        "Use 'no observed harmful activation on held-out adjacent negatives' instead of broad safety language.",
    ),
    ClaimPattern(
        re.compile(r"\ball\s+(?:production\s+)?MCP servers\b", re.IGNORECASE),
        "overclaim_scope",
        "Describe the scope as 'MCP-like, benchmark-converted, and explicitly marked synthetic tools'.",
    ),
    ClaimPattern(
        re.compile(r"\bcalibrated reliability\b", re.IGNORECASE),
        "overclaim_reliability",
        "Describe the score as a 'rule-based deployability score, not calibrated probability'.",
    ),
    ClaimPattern(
        re.compile(r"\blearned gating\b", re.IGNORECASE),
        "overclaim_reliability",
        "Describe the score as a 'rule-based deployability score, not calibrated probability'.",
    ),
    ClaimPattern(
        re.compile(r"\bend-to-end agent success\b", re.IGNORECASE),
        "overclaim_scope",
        "Limit the claim to structured tool-call or benchmark routing outcomes, not end-to-end agent success.",
    ),
)

README_FIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"safe enough to expose", re.IGNORECASE), "checked before exposure"),
    (re.compile(r"production safety guarantee", re.IGNORECASE), "deployment guarantee"),
    (
        re.compile(r"requires a governed representation layer", re.IGNORECASE),
        "can benefit substantially from a governed representation layer",
    ),
    (
        re.compile(r"all\s+production\s+MCP servers", re.IGNORECASE),
        "MCP-like, benchmark-converted, and explicitly marked synthetic tools",
    ),
    (
        re.compile(r"all\s+MCP servers", re.IGNORECASE),
        "MCP-like, benchmark-converted, and explicitly marked synthetic tools",
    ),
    (re.compile(r"calibrated reliability", re.IGNORECASE), "rule-based deployability"),
    (re.compile(r"learned gating", re.IGNORECASE), "rule-based gating"),
    (re.compile(r"end-to-end agent success", re.IGNORECASE), "benchmark tool-call success"),
    (re.compile(r"\| MCP-like tools \| 295 \|"), "| MCP-like tools | 290 |"),
    (
        re.compile(
            r"\| Total controls \| 2,950 \|\n"
            r"\| Development controls \| 1,475 \|\n"
            r"\| Held-out test controls \| 1,475 \|"
        ),
        "| Selected held-out controls | 1,450 |",
    ),
    (
        re.compile(r"same 1,475-control held-out test set"),
        "same 1,450-control selected held-out test set",
    ),
    (
        re.compile(r"\| Routing examples per distractor level \| 1,475 \|"),
        "| Routing examples per distractor level | See generated routing artifacts |",
    ),
    (
        re.compile(
            r"After validation and repair, the reported artifact set has no residual checker-level failures: "
            r"unsupported arguments, missing required fields, invalid enum values, malformed JSON examples, "
            r"contradictory guidance, and missing non-use boundaries are all recorded as 0\s*/\s*2950\."
        ),
        (
            "After validation and repair, the reported artifact audit records no residual checker-level "
            "failures for unsupported arguments, missing required fields, invalid enum values, malformed "
            "JSON examples, contradictory guidance, or missing non-use boundaries."
        ),
    ),
)


def scan_public_claims(
    paths: Sequence[str | Path],
    *,
    exclude_paths: Sequence[str | Path] | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    excluded = {_canonical_path(Path(path)) for path in (exclude_paths or [])}
    files = list(_iter_text_files(paths, warnings, excluded))
    issues: list[ClaimIssue] = []

    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            warnings.append(f"Skipping non-UTF-8 text file: {_display_path(path)}")
            continue
        lines = text.splitlines()
        for line_index, line in enumerate(lines):
            issues.extend(_scan_stale_values(path, line_index, line, lines))
            issues.extend(_scan_overclaims(path, line_index, line))

    issue_dicts = [asdict(issue) for issue in issues]
    return {
        "paths": [str(path) for path in paths],
        "scanned_files": len(files),
        "issue_count": len(issue_dicts),
        "issues": issue_dicts,
        "warnings": warnings,
    }


def write_public_claim_outputs(
    audit: dict[str, Any],
    *,
    output_json: str | Path,
    output_md: str | Path,
) -> dict[str, Path]:
    json_path = Path(output_json)
    md_path = Path(output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(build_public_claims_markdown(audit), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def build_public_claims_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Public Claims Audit",
        "",
        f"- Scanned files: {audit.get('scanned_files', 0)}",
        f"- Issues: {audit.get('issue_count', 0)}",
    ]
    warnings = audit.get("warnings", [])
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)

    issues = audit.get("issues", [])
    if not issues:
        lines.extend(["", "No public-claim issues found."])
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "",
            "## Issues",
            "",
            "| Path | Line | Issue | Matched text | Suggestion |",
            "| --- | ---: | --- | --- | --- |",
        ]
    )
    for issue in issues:
        lines.append(
            "| {path} | {line} | {issue_type} | `{matched}` | {suggestion} |".format(
                path=_escape_markdown_cell(str(issue["path"])),
                line=issue["line_number"],
                issue_type=_escape_markdown_cell(str(issue["issue_type"])),
                matched=_escape_backticks(str(issue["matched_text"])),
                suggestion=_escape_markdown_cell(str(issue["suggestion"])),
            )
        )
    return "\n".join(lines) + "\n"


def apply_public_claim_fixes(paths: Sequence[str | Path]) -> dict[str, Any]:
    fixed_files: list[str] = []
    warnings: list[str] = []
    for readme in _iter_requested_readmes(paths):
        if not readme.exists():
            warnings.append(f"README.md fix target is missing: {_display_path(readme)}")
            continue
        original = readme.read_text(encoding="utf-8")
        updated = original
        for pattern, replacement in README_FIXES:
            updated = pattern.sub(replacement, updated)
        if updated != original:
            readme.write_text(updated, encoding="utf-8")
            fixed_files.append(_display_path(readme))
    if not fixed_files:
        warnings.append("No README.md fixes were applied.")
    return {"fixed_files": fixed_files, "warnings": warnings}


def _scan_stale_values(path: Path, line_index: int, line: str, lines: Sequence[str]) -> list[ClaimIssue]:
    if _has_archival_marker(lines, line_index):
        return []
    issues: list[ClaimIssue] = []
    occupied_spans: list[tuple[int, int]] = []
    for pattern in STALE_VALUE_PATTERNS:
        for match in pattern.regex.finditer(line):
            if any(_spans_overlap(match.span(), span) for span in occupied_spans):
                continue
            occupied_spans.append(match.span())
            issues.append(
                ClaimIssue(
                    path=_display_path(path),
                    line_number=line_index + 1,
                    matched_text=match.group(0),
                    issue_type=pattern.issue_type,
                    suggestion=pattern.suggestion,
                )
            )
    return issues


def _scan_overclaims(path: Path, line_index: int, line: str) -> list[ClaimIssue]:
    issues: list[ClaimIssue] = []
    occupied_spans: list[tuple[int, int]] = []
    for pattern in OVERCLAIM_PATTERNS:
        for match in pattern.regex.finditer(line):
            if any(_spans_overlap(match.span(), span) for span in occupied_spans):
                continue
            occupied_spans.append(match.span())
            issues.append(
                ClaimIssue(
                    path=_display_path(path),
                    line_number=line_index + 1,
                    matched_text=match.group(0),
                    issue_type=pattern.issue_type,
                    suggestion=pattern.suggestion,
                )
            )
    return issues


def _has_archival_marker(lines: Sequence[str], line_index: int, window: int = 2) -> bool:
    start = max(0, line_index - window)
    end = min(len(lines), line_index + window + 1)
    nearby_text = "\n".join(lines[start:end]).lower()
    return any(marker in nearby_text for marker in ARCHIVAL_MARKERS)


def _iter_text_files(
    paths: Sequence[str | Path],
    warnings: list[str],
    excluded: set[Path],
) -> Iterable[Path]:
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            warnings.append(f"Missing path skipped: {path}")
            continue
        if path.is_file():
            if _canonical_path(path) in excluded:
                continue
            if _is_pdf(path):
                warnings.append(f"PDF skipped: {_display_path(path)}")
                continue
            if _is_text_file(path):
                yield path
            continue

        if _is_paper_pdf_only_directory(path):
            warnings.append(f"Paper source edits cannot be applied for {_display_path(path)}: only PDF files were found.")
        for child in sorted(path.rglob("*")):
            if not child.is_file():
                continue
            if _canonical_path(child) in excluded:
                continue
            if _is_pdf(child):
                warnings.append(f"PDF skipped: {_display_path(child)}")
                continue
            if _is_text_file(child):
                yield child


def _iter_requested_readmes(paths: Sequence[str | Path]) -> Iterable[Path]:
    seen: set[Path] = set()
    for raw_path in paths:
        path = Path(raw_path)
        candidates: list[Path]
        if path.name == "README.md":
            candidates = [path]
        elif path.is_dir():
            candidates = [child for child in path.rglob("README.md")]
        else:
            candidates = []
        for candidate in candidates:
            canonical = _canonical_path(candidate)
            if canonical not in seen:
                seen.add(canonical)
                yield candidate


def _is_pdf(path: Path) -> bool:
    return path.suffix.lower() == ".pdf"


def _is_text_file(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in BINARY_SUFFIXES:
        return False
    if suffix not in TEXT_SUFFIXES:
        return _looks_like_text(path)
    return _looks_like_text(path)


def _looks_like_text(path: Path) -> bool:
    try:
        sample = path.read_bytes()[:4096]
    except OSError:
        return False
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _is_paper_pdf_only_directory(path: Path) -> bool:
    if "paper" not in path.name.lower():
        return False
    pdfs = [child for child in path.rglob("*") if child.is_file() and child.suffix.lower() == ".pdf"]
    if not pdfs:
        return False
    source_suffixes = {".tex", ".md", ".rst", ".txt"}
    sources = [child for child in path.rglob("*") if child.is_file() and child.suffix.lower() in source_suffixes]
    return not sources


def _spans_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _canonical_path(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def _escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _escape_backticks(value: str) -> str:
    return value.replace("`", "\\`").replace("\n", " ")
