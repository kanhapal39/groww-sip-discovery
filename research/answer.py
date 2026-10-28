"""Grounded answers from the Golden Dataset.

1. Retrieve matching public Golden Dataset records (``research.retrieval``),
   drop duplicates, and keep only strong matches (a question tag, or enough of
   the question's words; a named investor segment must be tagged on the record).
2. If fewer than ``min_records`` match strongly, return the insufficiency
   message without calling a model.
3. Otherwise ask the LLM to summarise ONLY those records, citing them as R1..Rn
   and marking each point as stated in the evidence or inferred.
4. Drop any point that cites no valid record, quotes text that is not in the
   records it cites, gives a percentage the cited records do not contain,
   names an investor group that neither the question nor the cited records
   mention, or claims a product change will improve outcomes. Removed statements are
   returned with the reason, so the page can say what was removed. Quotes and
   links shown to users come from the stored records, never from the model's text.

Coverage figures and limitations are computed in code, not by the model.
Frequency words in the model's text ("mainly", "often") are not removed but
are flagged in the limitations, since the records cannot show how common anything is.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from research.analysis import EMPTY_VALUES, dedupe, text_key
from research.retrieval import search, segment_targets

INSUFFICIENT_MESSAGE = (
    "The Golden Dataset does not contain enough evidence to answer this question reliably."
)
PROMPT_VERSION = "answer-v2"

SYSTEM_PROMPT = """You are a research assistant summarising investor evidence about SIPs (Systematic Investment Plans).
You receive a question and numbered records (R1, R2, ...). Each record is a real public post or app review with AI-assigned tags.

Rules:
- Use ONLY the records. Do not use outside knowledge. Do not invent facts, quotes, numbers or percentages.
- Every point must cite at least one record ID that directly supports it. Put words in quotation marks only if they appear verbatim in a cited record.
- basis = "stated" if the records say it directly; "inferred" if it is a reasonable reading that the records do not state outright.
- Do not state why someone stopped, paused or cancelled unless the record says why.
- Do not describe investor groups (first-time, salaried, young) unless the records say so.
- If the records disagree or describe different situations, say so in a point.
- If the records do not address the question, set sufficient to false.
- Plain, neutral language. No product recommendations and no predictions about what a product change would do.

Return only JSON:
{"sufficient": true|false, "summary": "1-2 sentences", "points": [{"text": "...", "basis": "stated"|"inferred", "records": ["R1"]}], "gaps": "what the records cannot tell us"}"""

# Words inside straight or curly double quotes, at least three words long.
QUOTED = re.compile(r"[\"“”]([^\"“”]{3,}?)[\"“”]")
PERCENT = re.compile(r"\d+(?:\.\d+)?\s*(?:%|per ?cent\b)", re.IGNORECASE)
# Forward-looking claims about the effect of a product change.
IMPACT_CLAIM = re.compile(
    r"\b(will|would|could|should|can)\s+(likely\s+|help\s+|significantly\s+)?"
    r"(improve|increase|boost|raise|reduce|lower|prevent|cut|drive|lift)\w*\b.*\b(retention|continuation|churn|cancellation|lapse|stop)",
    re.IGNORECASE)
SHORT_QUOTE_WORDS = 5
# Investor groups a statement may only name if the question or the cited records do (EC21).
SEGMENT_CLAIMS: tuple[re.Pattern[str], ...] = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"\bfirst.?time (sip |mutual fund |mf )?(investors?|users?|buyers?)\b|\bnew (sip )?investors?\b|\bnew to (investing|sips?|mutual funds?)\b|\bbeginners?\b|\bnovices?\b|\bnewbies?\b",
    r"\bsalaried\b",
    r"\bself.?employed\b|\bfreelancers?\b|\bbusiness owners?\b",
    r"\bstudents?\b",
    r"\byoung(er)? (investors?|people|users?|adults?)\b|\bmillennials?\b|\bgen ?z\b",
    r"\bolder (investors?|people|users?)\b|\bretirees?\b|\bretired\b|\bsenior citizens?\b",
    r"\bwomen\b|\bfemale investors?\b",
    r"\bexperienced investors?\b|\blong.?term investors?\b|\bseasoned investors?\b",
))
# Words that claim how common something is (EC22); flagged, not removed.
FREQUENCY_WORDS = re.compile(
    r"\b(mainly|mostly|most|majority|often|frequently|commonly|common|typically|usually|generally|"
    r"primarily|predominantly|widespread|widely|many|numerous|the norm)\b", re.IGNORECASE)


def strong_matches(ranked: list[dict[str, Any]], min_coverage: float, min_term_hits: int = 2) -> list[dict[str, Any]]:
    """Records that match a question tag, or contain enough of the question's words.

    Word matching needs at least ``min_coverage`` of the question's words and at least ``min_term_hits`` of them
    (fewer only when the question has fewer words), so one shared keyword is not treated as relevance. When the
    question names an investor segment, only records tagged with that segment qualify.
    """
    out = []
    for r in ranked:
        segments = r.get("segment_targets") or []
        if len(r.get("segment_matched") or []) < len(segments):
            continue
        n_terms = r.get("query_terms", 0)
        hits = r.get("term_hits", round(r.get("term_coverage", 0) * n_terms))
        text_ok = r.get("term_coverage", 0) >= min_coverage and hits >= min(min_term_hits, n_terms)
        segment_only = bool(segments) and not n_terms and not r.get("tag_targets")
        if r["matched_tags"] or text_ok or segment_only:
            out.append(r)
    return out


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
        "undated": sum(1 for r in evidence if not r.get("year")),
        "individually_reviewed": sum(bool(r.get("individually_reviewed")) for r in evidence),
        "implied_tags": sum(bool(r.get("is_hypothesis")) for r in evidence),
    }


def limitations(evidence: list[dict[str, Any]], total_public: int, small_sample: int, recent_from: int | None = None,
                segments: list[str] | None = None, duplicates: int = 0) -> list[str]:
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
    if segments:
        notes.append(f"Segment ({', '.join(segments)}): only records with this AI-assigned tenure tag were used. Tenure is rarely stated "
                     "in public posts and the tag may be inferred, so findings are not established for this investor group.")
    behaviours = Counter(r.get("behavior") for r in evidence if r.get("behavior") not in EMPTY_VALUES)
    if len([b for b, c in behaviours.items() if c >= 2]) >= 2:
        mix = ", ".join(f"{b.replace('_', ' ')} {c}" for b, c in behaviours.most_common())
        notes.append(f"Mixed evidence: behaviour tags in these records are {mix}. Check each point against the records it cites.")
    if recent_from:
        older = sum(1 for r in evidence if r.get("year") and r["year"] < recent_from)
        if older:
            notes.append(f"{older} of {cov['records']} records were published before {recent_from}; the app behaviour they describe may have changed since.")
    if cov["undated"]:
        notes.append(f"{cov['undated']} of {cov['records']} records have no reliable publication date.")
    short = sum(1 for r in evidence if r.get("evidence_quote") and len(r["evidence_quote"].split()) < SHORT_QUOTE_WORDS)
    if short:
        notes.append(f"{short} records have a quote shorter than {SHORT_QUOTE_WORDS} words; open the record for its full context.")
    if duplicates:
        notes.append(f"{duplicates} duplicate record(s) with the same ID or text were removed before counting.")
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


def unsupported(text: str, sources: list[str], question: str = "") -> str | None:
    """Why ``text`` is not supported by the ``sources`` texts, or None if no check fails."""
    haystack = text_key(" ".join(sources))
    for pattern in SEGMENT_CLAIMS:
        named = pattern.search(text)
        if named and not pattern.search(question) and not any(pattern.search(s) for s in sources):
            return f"names an investor group (\"{named.group(0)}\") that the question and cited records do not mention"
    for quote in QUOTED.findall(text):
        if len(quote.split()) >= 3 and text_key(quote) not in haystack:
            return f"quotes words not found in the cited records: \"{quote.strip()}\""
    for pct in PERCENT.findall(text):
        number = re.match(r"\d+(?:\.\d+)?", pct).group(0)
        if not re.search(rf"(?<![\d.]){re.escape(number)}\s*(%|per ?cent)", " ".join(sources), re.IGNORECASE):
            return f"gives a percentage ({pct.strip()}) that the cited records do not contain"
    if IMPACT_CLAIM.search(text):
        return "predicts the effect of a product change, which the records cannot show"
    return None


def frequency_words(texts: list[str]) -> list[str]:
    """Distinct frequency words (lower-case, in order of first use) in ``texts``."""
    return list(dict.fromkeys(m.lower() for t in texts for m in FREQUENCY_WORDS.findall(t or "")))


def validate_points(payload: dict[str, Any], n_records: int, evidence: list[dict[str, Any]] | None = None,
                    removed: list[dict[str, str]] | None = None, question: str = "") -> list[dict[str, Any]]:
    """Keep points that cite at least one existing record; normalise basis.

    With ``evidence``, a point is also dropped when ``unsupported`` finds a problem against the records it cites.
    Dropped points are appended to ``removed`` with the reason.
    """
    valid = []
    for point in payload.get("points") or []:
        if not isinstance(point, dict) or not str(point.get("text") or "").strip():
            continue
        text = str(point["text"]).strip()
        refs = []
        for ref in point.get("records") or []:
            m = re.fullmatch(r"R(\d+)", str(ref).strip())
            if m and 1 <= int(m.group(1)) <= n_records:
                refs.append(int(m.group(1)))
        if not refs:
            if removed is not None:
                removed.append({"text": text, "reason": "cites no record in the evidence"})
            continue
        if evidence is not None:
            reason = unsupported(text, [evidence[i - 1].get("text") or "" for i in set(refs)], question)
            if reason:
                if removed is not None:
                    removed.append({"text": text, "reason": reason})
                continue
        basis = "inferred" if str(point.get("basis")).lower() == "inferred" else "stated"
        valid.append({"text": text, "basis": basis, "records": sorted(set(refs))})
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
    ranked, duplicates = dedupe(search(db_path, question, limit=settings["retrieve_limit"]))
    evidence = strong_matches(ranked, settings["min_term_coverage"])[: settings["max_evidence"]]
    segments = [f"{f}={v}" for f, v in segment_targets(question)]
    base = {"question": question, "evidence": evidence, "coverage": coverage(evidence), "duplicates_removed": duplicates,
            "limitations": limitations(evidence, total_public, settings["small_sample"], settings.get("recent_from_year"),
                                       segments, duplicates),
            "prompt_version": PROMPT_VERSION, "removed": []}
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
    removed: list[dict[str, str]] = []
    points = validate_points(payload, len(evidence), evidence, removed, question)
    usage = getattr(response, "usage", {}) or {}
    if not payload.get("sufficient", True) or not points:
        return {**base, "status": "insufficient", "message": INSUFFICIENT_MESSAGE, "removed": removed,
                "detail": "The matching records do not directly address this question.", "gaps": payload.get("gaps"),
                "tokens": usage.get("total_tokens")}
    summary = str(payload.get("summary") or "").strip()
    # The summary cites nothing, so it is checked against all evidence shown.
    reason = unsupported(summary, [r.get("text") or "" for r in evidence], question) if summary else None
    if reason:
        removed.append({"text": summary, "reason": f"summary {reason}"})
        summary = ""
    notes = list(base["limitations"])
    frequency = frequency_words([summary, *(p["text"] for p in points)])
    if frequency:
        notes.insert(0, f"The answer uses words about how common something is ({', '.join(frequency)}). These records are a "
                        f"selected sample of {len(evidence)}; they show that a situation occurs, not how often.")
    return {**base, "status": "answered", "summary": summary, "points": points, "removed": removed, "limitations": notes,
            "gaps": payload.get("gaps"), "tokens": usage.get("total_tokens")}
