"""Search and retrieval over the Golden Dataset index.

Two signals are combined: FTS5 BM25 over text, quote, reason, context and tag
words, and question-to-tag rules (e.g. "autopay" -> trigger mandate_or_payment).
A question that names an investor segment ("first-time", "beginner") also gets
segment targets; ``research.answer.strong_matches`` uses them as a filter, so
findings are only attributed to a segment when the records are tagged with it.
Only public (approved, eligible) records are returned.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

STOPWORDS = frozenset(
    "a an and are as at be by can do does for from has have how i in is it its my of on or so that the their them "
    "there they this to was were what when where which who why will with you your about after before during first "
    "investors investor people say said face problems problem sip sips "
    # Generic words that matched unrelated records (AI Eval Case C: "experience", "time", "setting up").
    "experience experiences time times setting set up get got getting use using want wants like just also most more "
    "much many some any other often usually common main reason reasons issue issues happen happens".split()
)
# Terms shorter than this match whole words only (stops "up" matching "upi" or "update").
MIN_PREFIX_LEN = 4

# Question words -> (tag field, value) boosts. Rules, not a model: easy to audit.
TAG_RULES: tuple[tuple[str, str, str], ...] = (
    (r"\bpaus\w*|\bskip\w*|\btemporar\w*", "behavior", "pause_sip"),
    (r"\bstop\w*|\bcancel\w*|\bquit\w*|\bexit\w*|\bdiscontinu\w*", "behavior", "stop_sip"),
    (r"\breduc\w*|\blower\w*|\bdecreas\w*", "behavior", "reduce_sip"),
    (r"\bstart\w*|\bbegin\w*|\bset(ting)?.?up\b|\bfirst sips?\b", "behavior", "start_sip"),
    (r"\bcontinu\w*|\bkeep\w*", "behavior", "continue_sip"),
    (r"\bincreas\w*|\bstep.?up|\btop.?up", "behavior", "increase_sip"),
    (r"\bautopay|\bauto.?pay|\bmandate\w*|\bauto.?debit|\bpayment\w*|\bupi\b|\bfail\w*", "trigger", "mandate_or_payment"),
    (r"\bautopay|\bauto.?pay|\bmandate\w*", "in_app_pain", "mandate_autopay"),
    (r"\breturn\w*|\bnav\b|\bxirr\b|\bnegative\b|\bloss\w*", "in_app_pain", "returns_nav_confusion"),
    (r"\breturn\w*|\bcrash\w*|\bmarket\w*|\bfall\w*|\bdip\w*|\bvolatil\w*|\bnegative\b", "trigger", "market_or_returns"),
    (r"\bfirst year\b", "tenure", "new_under_1y"),
    (r"\bmodif\w*|\bedit\w*|\bchang\w* (the |my )?(sip |debit |instal+ment )?(amount|date)|\bstep.?up", "in_app_pain", "sip_management"),
    (r"\bexpect\w*", "expectation", "wealth_growth"),
    (r"\bredeem\w*|\bredemption\w*|\bwithdraw\w*", "in_app_pain", "redemption_withdrawal"),
    (r"\bfee\w*|\bcharge\w*|\bcost\w*", "trigger", "fees_or_charges"),
    (r"\bsupport\b|\bcustomer care\b|\bhelp\w*", "trigger", "support"),
    (r"\btrust\w*|\bfraud\w*|\bscam\w*", "trigger", "trust_or_fraud_fear"),
    (r"\bfund selection|\bwhich fund\b|\bchoos\w*", "in_app_pain", "fund_selection"),
    (r"\bincome\b|\bjob\b|\bsalary\b|\bloan\w*|\bemergenc\w*|\bmoney need", "trigger", "money_need_or_income"),
)
# Question words naming an investor segment -> (tag field, value) the evidence must carry.
SEGMENT_RULES: tuple[tuple[str, str, str], ...] = (
    (r"\bfirst.?time\b|\bnew investors?\b|\bnew to (investing|sips?|mutual funds?)\b|\bbeginners?\b|\bnovices?\b",
     "tenure", "new_under_1y"),
)
TAG_BOOST = 2.0


def query_terms(question: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", question.lower())
    return [w for w in dict.fromkeys(words) if w not in STOPWORDS and len(w) > 1 and not w.isdigit()]


def tag_targets(question: str) -> list[tuple[str, str]]:
    q = question.lower()
    return list(dict.fromkeys((field, value) for pattern, field, value in TAG_RULES if re.search(pattern, q)))


def segment_targets(question: str) -> list[tuple[str, str]]:
    q = question.lower()
    return list(dict.fromkeys((field, value) for pattern, field, value in SEGMENT_RULES if re.search(pattern, q)))


def searchable(row: dict[str, Any], include_context: bool = True) -> str:
    """Text, quote, reason, tag words and (optionally) the thread context, lower-cased.

    Word matches that decide relevance exclude the context: a reply is not evidence just because its thread
    title matches (Edge Case 13). The FTS index still includes context for ranking.
    """
    from research.store import TAG_FIELDS

    parts = [row.get(k) or "" for k in ("text", "evidence_quote", "reason") + (("context",) if include_context else ())]
    parts += [str(row.get(f) or "").replace("_", " ") for f in TAG_FIELDS]
    return " ".join(parts).lower()


def stem(term: str) -> str:
    """Drop a common English ending ("starting" -> "start") if at least MIN_PREFIX_LEN letters remain."""
    for suffix in ("ing", "ed", "es", "s"):
        if term.endswith(suffix) and len(term) - len(suffix) >= MIN_PREFIX_LEN:
            return term[: -len(suffix)]
    return term


def term_hits(terms: list[str], text: str) -> int:
    """Number of query terms that appear as a word, or (stemmed) as a word prefix if the term is long enough."""
    words = set(re.findall(r"[a-z0-9]+", text))
    return sum(1 for t in terms if t in words or (len(t) >= MIN_PREFIX_LEN and any(w.startswith(stem(t)) for w in words)))


def term_coverage(terms: list[str], text: str) -> float:
    """Share of query terms that appear in ``text`` (see ``term_hits``)."""
    return term_hits(terms, text) / len(terms) if terms else 0.0


def fts_query(terms: list[str]) -> str:
    """OR of prefix terms, each quoted so user input cannot inject FTS syntax."""
    return " OR ".join(f'"{t}"*' for t in terms)


def search(db_path: Path, question: str, limit: int = 12, public_only: bool = True) -> list[dict[str, Any]]:
    """Ranked records with ``score``, ``matched_tags``, ``term_coverage``, ``term_hits`` and segment matches attached.

    ``query_terms`` and ``tag_targets`` (counts for the question) are attached so callers can judge match strength.
    """
    from research.store import BOOL_COLUMNS, public_view

    if not db_path.exists():
        return []
    terms = query_terms(question)
    targets = tag_targets(question)
    segments = segment_targets(question)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = {r["record_id"]: dict(r) for r in con.execute("SELECT * FROM golden" + (" WHERE public = 1" if public_only else ""))}
    text_scores: dict[str, float] = {}
    if terms:
        for r in con.execute("SELECT record_id, bm25(golden_fts) AS s FROM golden_fts WHERE golden_fts MATCH ?", (fts_query(terms),)):
            text_scores[r["record_id"]] = -float(r["s"])  # bm25: lower is better
    con.close()

    top = max(text_scores.values(), default=0.0) or 1.0
    ranked = []
    for record_id, row in rows.items():
        matched = [f"{f}={v}" for f, v in targets if row.get(f) == v]
        segment_matched = [f"{f}={v}" for f, v in segments if row.get(f) == v]
        hits = term_hits(terms, searchable(row, include_context=False))
        context_hits = term_hits(terms, (row.get("context") or "").lower()) if row.get("context") else 0
        coverage = hits / len(terms) if terms else 0.0
        # Coverage (share of question words present) is absolute; bm25 only breaks ties.
        score = (coverage + TAG_BOOST * len(matched) / max(len(targets), 1) + TAG_BOOST * len(segment_matched) / max(len(segments), 1)
                 + 0.1 * text_scores.get(record_id, 0.0) / top)
        if not matched and not segment_matched and coverage == 0 and context_hits == 0:
            continue
        for c in BOOL_COLUMNS:
            row[c] = None if row[c] is None else bool(row[c])
        if row.get("year") is not None:
            row["year"] = int(row["year"])
        ranked.append({**(public_view(row) if public_only else row), "score": round(score, 3), "matched_tags": matched,
                       "term_coverage": round(coverage, 2), "term_hits": hits, "context_hits": context_hits, "query_terms": len(terms),
                       "tag_targets": len(targets), "segment_targets": [f"{f}={v}" for f, v in segments],
                       "segment_matched": segment_matched})
    ranked.sort(key=lambda r: (-r["score"], r["record_id"]))
    return ranked[:limit]
