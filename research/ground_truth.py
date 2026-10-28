"""Independently labelled evaluation set (docs/ai_eval_ground_truth_template.md).

Usage:
    python -m research.ground_truth sample --size 20 --seed 20261028 --exclude ID_PREFIX,...
    python -m research.ground_truth compare

``sample`` draws records at random (fixed seed) from the public Golden Dataset
export and writes a labelling workbook that shows the text, source and context
but none of the engine's tags, reasons or answers. ``compare`` reads the
labeller's workbook and reports agreement with the engine per field, with the
number of labelled records as the denominator. It never fills in a label.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from research.opportunities import load_definitions, matches
from research.store import load_golden

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SHEET_PATH = PROJECT_ROOT / "data" / "review" / "ground_truth_20.xlsx"
PUBLIC_PATH = PROJECT_ROOT / "data" / "export" / "golden_public.jsonl"
LABEL_FIELDS = ("behavior", "in_app_pain", "unmet_need", "tenure")
SHOWN = ("n", "record_id", "source", "source_url", "published_at", "context", "text")
LABELS = ("relevant", *LABEL_FIELDS, "theme", "basis", "labeller_notes")
NO_THEME = "none"


def sample(rows: list[dict[str, Any]], size: int, seed: int, exclude: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    """``size`` rows chosen at random with ``seed``, skipping record IDs that start with any ``exclude`` prefix."""
    pool = sorted((r for r in rows if not (exclude and str(r.get("record_id")).startswith(tuple(exclude)))),
                  key=lambda r: str(r["record_id"]))
    if size > len(pool):
        raise ValueError(f"asked for {size} records but only {len(pool)} are eligible")
    return random.Random(seed).sample(pool, size)


def allowed_values(codebook: dict[str, Any]) -> dict[str, list[tuple[str, str]]]:
    """{field: [(value, definition)]} for the labelled codebook fields."""
    return {f["id"]: [(v["id"], v["definition"]) for v in f["values"]] for f in codebook["fields"] if f["id"] in LABEL_FIELDS}


def write_sheet(path: Path, picked: list[dict[str, Any]], codebook: dict[str, Any], themes: list[str], meta: dict[str, str]) -> None:
    """Labelling workbook: records without engine tags, empty label columns with drop-down lists, and a codebook sheet."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.worksheet.datavalidation import DataValidation

    values = allowed_values(codebook)
    choices = {"relevant": ["yes", "no"], **{f: [v for v, _ in values[f]] for f in LABEL_FIELDS},
               "theme": [*themes, NO_THEME], "basis": ["stated", "inferred"]}
    wb = Workbook()
    ws = wb.active
    ws.title = "labels"
    header = [*SHOWN, *LABELS]
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    widths = {"text": 70, "context": 40, "source_url": 18, "record_id": 14, "labeller_notes": 30}
    for i, name in enumerate(header, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = widths.get(name, 16)
    for n, r in enumerate(picked, 1):
        ws.append([n, r["record_id"], r.get("source"), r.get("source_url"), str(r.get("published_at") or "unknown")[:10],
                   r.get("context") or "", r.get("text") or "", *[""] * len(LABELS)])
        link = ws.cell(ws.max_row, header.index("source_url") + 1)
        link.hyperlink, link.font = r.get("source_url"), Font(color="0563C1", underline="single")
        for cell in ws[ws.max_row]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    last = max(ws.max_row, 2)
    for name, options in choices.items():
        # Excel limits an inline list to 255 characters; longer lists point at the codebook sheet instead.
        inline = '"' + ",".join(options) + '"'
        col = ws.cell(1, header.index(name) + 1).column_letter
        dv = DataValidation(type="list", formula1=inline if len(inline) <= 255 else f"=lists!${col}$2:${col}${len(options) + 1}",
                            allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"{col}2:{col}{last}")
    ws.freeze_panes = "C2"

    lists = wb.create_sheet("lists")
    for name, options in choices.items():
        col = header.index(name) + 1
        lists.cell(1, col, name)
        for row, option in enumerate(options, 2):
            lists.cell(row, col, option)
    book = wb.create_sheet("codebook")
    book.append(["field", "value", "definition"])
    for field, vals in values.items():
        for value, definition in vals:
            book.append([field, value, definition])
    book.append([])
    for rule in codebook.get("rules", []):
        book.append(["rule", "", rule])
    about = wb.create_sheet("about")
    for key, value in meta.items():
        about.append([key, value])
    about.append(["instructions", "Label from the text, link and context only. Do not open the dashboard or the review workbook "
                                  "for these records until every label is final. Use 'unclear' when the text gives nothing."])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def read_labels(path: Path) -> dict[str, dict[str, str]]:
    """{record_id: {label: value}} for rows with at least one label filled in."""
    from openpyxl import load_workbook

    ws = load_workbook(path, read_only=True)["labels"]
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))
    out = {}
    for row in rows:
        values = dict(zip(header, row))
        labels = {k: str(values.get(k) or "").strip() for k in LABELS}
        if any(labels[k] for k in ("relevant", *LABEL_FIELDS, "theme")):
            out[str(values["record_id"])] = labels
    return out


def compare(labels: dict[str, dict[str, str]], golden: list[dict[str, Any]], definitions: dict[str, Any]) -> dict[str, Any]:
    """Per-field agreement between the labeller and the engine. Each denominator counts only records with that label."""
    engine = {str(r["record_id"]): r for r in golden}
    fields: dict[str, dict[str, int]] = {f: {"labelled": 0, "agree": 0} for f in (*LABEL_FIELDS, "theme")}
    disagreements = []
    missing = [rid for rid in labels if rid not in engine]
    for rid, label in labels.items():
        row = engine.get(rid)
        if row is None:
            continue
        themes = [d["id"] for d in definitions["opportunities"] if matches(row, d)]
        for field in fields:
            if not label.get(field):
                continue
            fields[field]["labelled"] += 1
            agree = (label[field] in themes or (label[field] == NO_THEME and not themes)) if field == "theme" else label[field] == row.get(field)
            fields[field]["agree"] += agree
            if not agree:
                disagreements.append({"record_id": rid, "field": field, "label": label[field],
                                      "engine": themes if field == "theme" else row.get(field)})
    relevant = [l["relevant"] for l in labels.values() if l.get("relevant")]
    return {"records_labelled": len(labels), "not_in_golden": missing, "fields": fields,
            "labelled_relevant": {"yes": relevant.count("yes"), "no": relevant.count("no")},
            "disagreements": disagreements}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("sample", help="write the labelling workbook")
    s.add_argument("--size", type=int, default=20)
    s.add_argument("--seed", type=int, required=True)
    s.add_argument("--exclude", default="", help="comma-separated record ID prefixes to leave out")
    s.add_argument("--force", action="store_true", help="overwrite an existing workbook (destroys labels)")
    sub.add_parser("compare", help="compare filled-in labels with the engine")
    args = parser.parse_args(argv)

    with (PROJECT_ROOT / "codebook.yaml").open(encoding="utf-8") as fh:
        codebook = yaml.safe_load(fh)
    definitions = load_definitions()
    golden = load_golden(PUBLIC_PATH)
    if args.command == "sample":
        if SHEET_PATH.exists() and not args.force:
            print(f"{SHEET_PATH.relative_to(PROJECT_ROOT)} exists; it may hold labels. Use --force to overwrite.")
            return 1
        exclude = tuple(p.strip() for p in args.exclude.split(",") if p.strip())
        picked = sample(golden, args.size, args.seed, exclude)
        meta = {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seed": str(args.seed),
                "size": str(args.size), "pool": f"{PUBLIC_PATH.relative_to(PROJECT_ROOT)} ({len(golden)} rows)",
                "excluded_prefixes": ",".join(exclude) or "none",
                "command": " ".join(["python -m research.ground_truth", *(argv if argv is not None else sys.argv[1:])])}
        write_sheet(SHEET_PATH, picked, codebook, [d["id"] for d in definitions["opportunities"]], meta)
        print(f"Wrote {len(picked)} records to {SHEET_PATH.relative_to(PROJECT_ROOT)}")
        for n, r in enumerate(picked, 1):
            print(f"{n:>2}. {r['record_id'][:8]} [{r.get('source')}] {' '.join((r.get('text') or '').split())[:90]}")
        return 0
    if not SHEET_PATH.exists():
        print("No labelling workbook; run the sample command first.")
        return 1
    labels = read_labels(SHEET_PATH)
    if not labels:
        print("No labels filled in yet.")
        return 1
    print(json.dumps(compare(labels, golden, definitions), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
