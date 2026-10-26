"""Export module — skeleton interface.

Responsibility: Define the future interface for exporting validated records.
Ensures future exports can distinguish ordinary tagged candidates from
human-approved Golden Dataset records.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ExportFormat:
    """Supported export formats."""

    CSV = "csv"
    JSONL = "jsonl"
    EXCEL = "xlsx"


@dataclass(frozen=True)
class ExportResult:
    """Result of exporting records."""

    output_path: str
    format: str
    record_count: int
    golden_dataset_count: int  # Records approved for the Golden Dataset


def export_records(
    records: list[dict[str, Any]],
    output_path: str,
    export_format: str = ExportFormat.JSONL,
    golden_dataset: bool = False,
) -> ExportResult:
    """Export validated records to a file.

    Stub for the future export implementation. Validates input and raises
    NotImplementedError — no file is written and no data is exported.

    Args:
        records: A list of validated record dictionaries.
        output_path: Destination file path.
        export_format: One of ExportFormat values.
        golden_dataset: If True, marks records as Golden Dataset (human-
            approved) rather than ordinary tagged candidates.

    Returns:
        An ExportResult instance.

    Raises:
        ValueError: If required arguments are missing or invalid.
        NotImplementedError: Always, since export is not yet implemented.
    """
    if not records:
        raise ValueError("records must not be empty")
    if not output_path:
        raise ValueError("output_path is required")
    if export_format not in (ExportFormat.CSV, ExportFormat.JSONL, ExportFormat.EXCEL):
        raise ValueError(f"Unsupported export format: {export_format}")

    raise NotImplementedError(
        "Export is not yet implemented. "
        "Stage 6 (validation and export) must be authorized before the export "
        "logic is built."
    )


# --- Golden Dataset review workflow -------------------------------------------
#
# Tagged rows become Golden Dataset *candidates* in a review workbook. Only rows
# a human marks "approved" in that workbook are promoted to data/manual/.
#
# Usage:
#     python -m pipeline.export review   # data/review/golden_candidates.xlsx
#     python -m pipeline.export golden   # approved rows -> data/manual/golden_dataset.jsonl

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REVIEW_STATUSES = ("pending", "approved", "rejected", "needs_revision")
TAG_COLUMNS = (
    "behavior", "lapse_type", "trigger", "expectation", "checking", "check_frequency", "in_app_pain",
    "emotion", "outside_action", "tenure", "income_stability", "age_band", "money_source", "influencer", "unmet_need",
)
COLUMNS = (
    ("review_status", 14), ("reviewer", 12), ("reviewer_notes", 30), ("stratum", 22), ("record_id", 12), ("source_url", 20),
    ("app_id", 18), ("year", 6), ("relevance", 9), ("text", 60), ("evidence_quote", 40), ("quote_status", 10),
    *((c, 16) for c in TAG_COLUMNS),
    ("confidence", 9), ("is_hypothesis", 9), ("reason", 30), ("tagged_by", 18), ("prompt_version", 10), ("codebook_version", 8),
)


def write_review_workbook(tag_rows: list[dict[str, Any]], texts: dict[str, str], path: Path) -> int:
    """Write successfully tagged rows to an Excel workbook for human review.

    Every row starts as "pending". Source URLs are clickable. Returns the
    number of rows written.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.worksheet.datavalidation import DataValidation

    rows = [r for r in tag_rows if r.get("status") == "ok"]
    wb = Workbook()
    ws = wb.active
    ws.title = "candidates"
    ws.append([name for name, _ in COLUMNS])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for index, (_, width) in enumerate(COLUMNS, 1):
        ws.column_dimensions[ws.cell(1, index).column_letter].width = width
    for row in rows:
        values = {**row, "review_status": "pending", "reviewer": "", "reviewer_notes": "", "text": texts.get(row["record_id"], ""),
                  "tagged_by": row.get("tagged_by") or row.get("model")}
        ws.append([values.get(name) for name, _ in COLUMNS])
        link = ws.cell(ws.max_row, [n for n, _ in COLUMNS].index("source_url") + 1)
        link.hyperlink, link.font = row["source_url"], Font(color="0563C1", underline="single")
        for cell in ws[ws.max_row]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    status = DataValidation(type="list", formula1='"' + ",".join(REVIEW_STATUSES) + '"', allow_blank=False)
    ws.add_data_validation(status)
    status.add(f"A2:A{max(ws.max_row, 2)}")
    ws.freeze_panes = "B2"
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return len(rows)


def source_group(row: dict[str, Any]) -> str:
    """Reddit, or the Play Store app, so every app counts as its own source."""
    return row.get("app_id") or row.get("source") or "unknown"


def golden_sample(tag_rows: list[dict[str, Any]], size: int, seed: int) -> list[dict[str, Any]]:
    """Up to ``size`` tagged rows spread across source × behaviour.

    Rows are taken one at a time from each (source, behaviour) cell in turn, in
    random order within a cell, so rare behaviours keep every row they have and
    common ones cannot crowd them out. Each row gets a ``stratum`` label.
    """
    import random
    from collections import defaultdict

    cells: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in tag_rows:
        if row.get("status") == "ok":
            cells[(source_group(row), row.get("behavior") or "unclear")].append(row)
    rng = random.Random(seed)
    for key in sorted(cells):
        rng.shuffle(cells[key])
    sample: list[dict[str, Any]] = []
    while len(sample) < size and any(cells.values()):
        for key in sorted(cells):
            if cells[key] and len(sample) < size:
                sample.append({**cells[key].pop(), "stratum": f"{key[0]} | {key[1]}"})
    return sample


def reviewed_count(path: Path) -> int:
    """Rows whose review_status is no longer "pending"."""
    from openpyxl import load_workbook

    ws = load_workbook(path, read_only=True).active
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))
    column = header.index("review_status")
    return sum(1 for values in rows if str(values[column] or "pending").strip().lower() != "pending")


PROVENANCE_FIELDS = ("source", "collected_at", "published_at", "context", "kind", "subreddit", "rating", "language")


def add_provenance(rows: list[dict[str, Any]], clean_path: Path) -> list[dict[str, Any]]:
    """Copy provenance from the clean record (same record_id) onto each approved row.

    The review workbook does not carry collection timestamps or platform, so
    they are joined here. Rows whose clean record is missing are rejected,
    because a Golden Dataset row must carry full provenance.
    """
    wanted = {r["record_id"] for r in rows}
    clean: dict[str, dict[str, Any]] = {}
    with clean_path.open(encoding="utf-8") as fh:
        for record in map(json.loads, fh):
            if record["record_id"] in wanted:
                clean[record["record_id"]] = record
    out = []
    for row in rows:
        record = clean.get(row["record_id"])
        if record is None or not record.get("collected_at"):
            raise ValueError(f"approved row {row['record_id']} has no clean record with a collection timestamp")
        metadata = record.get("metadata") or {}
        out.append({
            **row,
            "source": record.get("source"),
            "collected_at": record["collected_at"],
            "published_at": metadata.get("reviewed_at") or metadata.get("published_at"),
            "context": record.get("context"),
            "kind": metadata.get("kind") or ("review" if record.get("source") == "play_store" else None),
            "subreddit": metadata.get("subreddit"),
            "rating": metadata.get("rating"),
            "language": record.get("language"),
        })
    return out


def read_approved(path: Path) -> list[dict[str, Any]]:
    """Rows a reviewer marked "approved", with reviewer fields kept."""
    from openpyxl import load_workbook

    ws = load_workbook(path, read_only=True).active
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))
    approved = []
    for values in rows:
        row = dict(zip(header, values))
        if str(row.get("review_status") or "").strip().lower() == "approved":
            if not row.get("record_id") or not row.get("source_url"):
                raise ValueError(f"approved row is missing provenance: {row.get('record_id')}")
            approved.append(row)
    return approved


def main(argv: list[str] | None = None) -> int:
    import argparse

    import yaml

    parser = argparse.ArgumentParser(description="Golden Dataset review workflow.")
    parser.add_argument("mode", choices=["review", "sample", "golden"])
    parser.add_argument("--size", type=int, default=300, help="sample/golden: number of rows (names the workbook)")
    parser.add_argument("--force", action="store_true", help="replace a workbook that already has reviewed rows")
    parser.add_argument("--tagged-by", help="sample: only rows tagged by this model ID")
    parser.add_argument("--app", help="only rows for this app ID; the workbook name gets its last part")
    args = parser.parse_args(argv)
    with (PROJECT_ROOT / "config.yaml").open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    processed = PROJECT_ROOT / config["paths"]["processed"]
    suffix = f"_{args.app.rsplit('.', 1)[-1]}" if args.app else ""
    workbook = PROJECT_ROOT / config["paths"]["review"] / (
        f"golden_sample_{args.size}.xlsx" if args.mode in ("sample", "golden") else f"golden_candidates{suffix}.xlsx")

    if args.mode in ("review", "sample"):
        if workbook.exists() and reviewed_count(workbook) and not args.force:
            print(f"{workbook.relative_to(PROJECT_ROOT)} already has {reviewed_count(workbook)} reviewed rows; "
                  "not overwriting (use --force to replace it)", file=sys.stderr)
            return 1
        tag_rows = []
        for entry in config["pipeline"]["tagging"]["models"]:
            path = processed / entry["results_file"]
            if path.exists():
                with path.open(encoding="utf-8") as fh:
                    tag_rows += [r for r in map(json.loads, fh) if not args.app or r.get("app_id") == args.app]
        with (processed / "clean.jsonl").open(encoding="utf-8") as fh:
            texts = {r["record_id"]: r["text"] for r in map(json.loads, fh)}
        if args.mode == "sample":
            if args.tagged_by:
                tag_rows = [r for r in tag_rows if (r.get("tagged_by") or r.get("model")) == args.tagged_by]
            tag_rows = golden_sample(tag_rows, args.size, config["pipeline"]["tagging"]["sample_seed"])
            from collections import Counter

            for label, key in (("source", source_group), ("behavior", lambda r: r.get("behavior")), ("tagged_by", lambda r: r.get("tagged_by"))):
                print(f"By {label}: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(map(key, tag_rows)).items())))
        count = write_review_workbook(tag_rows, texts, workbook)
        print(f"Wrote {count} candidates (all pending) to {workbook.relative_to(PROJECT_ROOT)}")
        return 0

    approved = add_provenance(read_approved(workbook), processed / "clean.jsonl")
    out = PROJECT_ROOT / config["golden_dataset"]["manual_path"] / "golden_dataset.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for row in approved:
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    print(f"Promoted {len(approved)} approved rows to {out.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
