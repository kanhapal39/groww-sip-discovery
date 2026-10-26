"""Grounded answers from the Golden Dataset.

1. Retrieve matching public Golden Dataset records (``research.retrieval``).
2. If fewer than ``min_records`` match strongly, return the insufficiency
   message without calling a model.
3. Otherwise ask the LLM to summarise ONLY those records, citing them as R1..Rn
   and marking each point as stated in the evidence or inferred.
4. Drop any point that cites no valid record. Quotes and links shown to users
   come from the stored records, never from the model's text.

Coverage figures and limitations are computed in code, not by the model.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from research.retrieval import search

INSUFFICIENT_MESSAGE = (
    "The Golden Dataset does not contain enough evidence to answer this question reliably."
)
PROMPT_VERSION = "answer-v1"

SYSTEM_PROMPT = """You are a research assistant summarising investor evidence about SIPs (Systematic Investment Plans).
You receive a question and numbered records (R1, R2, ...). Each record is a real public post or app review with AI-assigned tags.

Rules:
- Use ONLY the records. Do not use outside knowledge. Do not invent facts, quotes, numbers or percentages.
- Every point must cite at least one record ID that directly supports it.
- basis = "stated" if the records say it directly; "inferred" if it is a reasonable reading that the records do not state outright.
- If the records do not address the question, set sufficient to false.
- Plain, neutral language. No product recommendations.

Return only JSON:
{"sufficient": true|false, "summary": "1-2 sentences", "points": [{"text": "...", "basis": "stated"|"inferred", "records": ["R1"]}], "gaps": "what the records cannot tell us"}"""


def strong_matches(ranked: list[dict[str, Any]], min_coverage: float) -> list[dict[str, Any]]:
    """Records that match a question tag, or contain at least ``min_coverage`` of the question's words."""
    return [r for r in ranked if r["matched_tags"] or r.get("term_coverage", 0) >= min_coverage]


def record_block(index: int, r: dict[str, Any], max_words: int) -> str:
    words = (r.get("text") or "").split()
    text = " ".join(words[:max_words]) + (" …" if len(words) > max_words else "")
    tags = ", ".join(f"{f}={r.get(f)}" for f in ("behavior", "lapse_type", "trigger", "in_app_pain", "emotion", "unmet_need")
                     if r.get(f) not in (None, "unclear", "none", "no_lapse"))
    where = f"{r.get('source')} {r.get('platform_detail')}, {str(r.get('published_at') or 'date unknown')[:10]}"
    context = f"\nThread: {' '.join((r.get('context') or '').split()[:25])}" if r.get("context") else ""
    return f"R{index} [{where}] tags: {tags or 'none'}{context}\nText: {text}"


def coverage(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    years = sorted(r["year"] for r in evidence if r.get("year"))
    return {
        "records": len(evidence),
        "sources": dict(Counter(r.get("source") for r in evidence)),
        "platforms": dict(Counter(r.get("platform_detail") for r in evidence)),
        "years": (years[0], years[-1]) if years else None,
        "individually_reviewed": sum(bool(r.get("individually_reviewed")) for r in evidence),
        "implied_tags": sum(bool(r.get("is_hypothesis")) for r in evidence),
    }


def limitations(evidence: list[dict[str, Any]], total_public: int, small_sample: int) -> list[str]:
    cov = coverage(evidence)
    notes = []
    if cov["records"] < small_sample:
        notes.append(f"Small sample: {cov['records']} matching records.")
    if len(cov["sources"]) == 1:
        notes.append(f"Single source platform ({next(iter(cov['sources']))}).")
    if cov["individually_reviewed"] < cov["records"]:
        notes.append(f"{cov['records'] - cov['individually_reviewed']} of {cov['records']} records were bulk-approved without row-by-row human review; tags are AI output.")
    if cov["implied_tags"]:
        notes.append(f"{cov['implied_tags']} records carry tags the model marked as implied rather than stated.")
    notes.append(f"Retrieved from {total_public} public Golden Dataset records by keyword and tag matching; relevant records using other wording may be missed.")
    notes.append("Public reviews and posts over-represent people with problems; this is not a representative sample of all investors.")
    return notes


def parse_model_json(content: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", content or "", re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def validate_points(payload: dict[str, Any], n_records: int) -> list[dict[str, Any]]:
    """Keep points that cite at least one existing record; normalise basis."""
    valid = []
    for point in payload.get("points") or []:
        if not isinstance(point, dict) or not str(point.get("text") or "").strip():
            continue
        refs = []
        for ref in point.get("records") or []:
            m = re.fullmatch(r"R(\d+)", str(ref).strip())
            if m and 1 <= int(m.group(1)) <= n_records:
                refs.append(int(m.group(1)))
        if refs:
            basis = "inferred" if str(point.get("basis")).lower() == "inferred" else "stated"
            valid.append({"text": str(point["text"]).strip(), "basis": basis, "records": sorted(set(refs))})
    return valid


def answer_question(
    question: str,
    db_path: Path,
    complete: Callable[[list[dict[str, str]]], Any] | None,
    settings: dict[str, Any],
    total_public: int,
) -> dict[str, Any]:
    """Return a dict with status: answered | insufficient | no_model | error."""
    question = question.strip()
    ranked = search(db_path, question, limit=settings["retrieve_limit"])
    evidence = strong_matches(ranked, settings["min_term_coverage"])[: settings["max_evidence"]]
    base = {"question": question, "evidence": evidence, "coverage": coverage(evidence),
            "limitations": limitations(evidence, total_public, settings["small_sample"]), "prompt_version": PROMPT_VERSION}
    if len(evidence) < settings["min_records"]:
        return {**base, "status": "insufficient", "message": INSUFFICIENT_MESSAGE,
                "detail": f"Found {len(evidence)} strongly matching record(s); at least {settings['min_records']} are required."}
    if complete is None:
        return {**base, "status": "no_model", "message": "The answer model is not configured, so only the matching evidence is shown."}

    blocks = "\n\n".join(record_block(i, r, settings["max_record_words"]) for i, r in enumerate(evidence, 1))
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Question: {question}\n\nRecords:\n{blocks}"}]
    try:
        response = complete(messages)
    except Exception as exc:  # rate limits, network, provider errors
        return {**base, "status": "error", "message": f"The research assistant could not generate an answer ({type(exc).__name__}). Matching evidence is shown below."}
    payload = parse_model_json(getattr(response, "content", response))
    if payload is None:
        return {**base, "status": "error", "message": "The model reply could not be read. Matching evidence is shown below."}
    points = validate_points(payload, len(evidence))
    if not payload.get("sufficient", True) or not points:
        return {**base, "status": "insufficient", "message": INSUFFICIENT_MESSAGE,
                "detail": "The matching records do not directly address this question.", "gaps": payload.get("gaps")}
    usage = getattr(response, "usage", {}) or {}
    return {**base, "status": "answered", "summary": str(payload.get("summary") or "").strip(), "points": points,
            "gaps": payload.get("gaps"), "tokens": usage.get("total_tokens")}
