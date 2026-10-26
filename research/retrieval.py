"""Search and retrieval over the Golden Dataset index.

Two signals are combined: FTS5 BM25 over text, quote, reason, context and tag
words, and question-to-tag rules (e.g. "autopay" -> trigger mandate_or_payment).
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
    "investors investor people say said face problems problem sip sips".split()
)

# Question words -> (tag field, value) boosts. Rules, not a model: easy to audit.
TAG_RULES: tuple[tuple[str, str, str], ...] = (
    (r"\bpaus\w*|\bskip\w*", "behavior", "pause_sip"),
    (r"\bstop\w*|\bcancel\w*|\bquit\w*|\bexit\w*", "behavior", "stop_sip"),
    (r"\breduc\w*|\blower\w*", "behavior", "reduce_sip"),
    (r"\bstart\w*|\bbegin\w*|\bnew\b|\bfirst\b", "behavior", "start_sip"),
    (r"\bcontinu\w*|\bkeep\w*", "behavior", "continue_sip"),
    (r"\bincreas\w*|\bstep.?up|\btop.?up", "behavior", "increase_sip"),
    (r"\bautopay|\bauto.?pay|\bmandate\w*|\bauto.?debit|\bpayment\w*|\bupi\b|\bfail\w*", "trigger", "mandate_or_payment"),
    (r"\bautopay|\bauto.?pay|\bmandate\w*", "in_app_pain", "mandate_autopay"),
    (r"\breturn\w*|\bnav\b|\bxirr\b|\bnegative\b|\bloss\w*", "in_app_pain", "returns_nav_confusion"),
    (r"\breturn\w*|\bcrash\w*|\bmarket\w*|\bfall\w*|\bdip\w*|\bvolatil\w*|\bnegative\b", "trigger", "market_or_returns"),
    (r"\bfirst year\b|\bnew\b|\bbeginner\w*|\bstart\w*", "tenure", "new_under_1y"),
    (r"\bexpect\w*", "expectation", "wealth_growth"),
    (r"\bredeem\w*|\bredemption\w*|\bwithdraw\w*", "in_app_pain", "redemption_withdrawal"),
    (r"\bfee\w*|\bcharge\w*|\bcost\w*", "trigger", "fees_or_charges"),
    (r"\bsupport\b|\bcustomer care\b|\bhelp\w*", "trigger", "support"),
    (r"\btrust\w*|\bfraud\w*|\bscam\w*", "trigger", "trust_or_fraud_fear"),
    (r"\bfund selection|\bwhich fund\b|\bchoos\w*", "in_app_pain", "fund_selection"),
    (r"\bincome\b|\bjob\b|\bsalary\b|\bloan\w*|\bemergenc\w*|\bmoney need", "trigger", "money_need_or_income"),
)
TAG_BOOST = 2.0


def query_terms(question: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", question.lower())
    return [w for w in dict.fromkeys(words) if w not in STOPWORDS and len(w) > 1]


def tag_targets(question: str) -> list[tuple[str, str]]:
    q = question.lower()
    return list(dict.fromkeys((field, value) for pattern, field, value in TAG_RULES if re.search(pattern, q)))


def searchable(row: dict[str, Any]) -> str:
    from research.store import TAG_FIELDS

    parts = [row.get(k) or "" for k in ("text", "evidence_quote", "reason", "context")]
    parts += [str(row.get(f) or "").replace("_", " ") for f in TAG_FIELDS]
    return " ".join(parts).lower()


def term_coverage(terms: list[str], text: str) -> float:
    """Share of query terms that appear as a word or word prefix in ``text``."""
    if not terms:
        return 0.0
    words = set(re.findall(r"[a-z0-9]+", text))
    hit = sum(1 for t in terms if t in words or any(w.startswith(t) for w in words))
    return hit / len(terms)


def fts_query(terms: list[str]) -> str:
    """OR of prefix terms, each quoted so user input cannot inject FTS syntax."""
    return " OR ".join(f'"{t}"*' for t in terms)


def search(db_path: Path, question: str, limit: int = 12, public_only: bool = True) -> list[dict[str, Any]]:
    """Ranked records with ``score``, ``matched_tags`` and ``text_match`` attached."""
    from research.store import BOOL_COLUMNS, public_view

    if not db_path.exists():
        return []
    terms = query_terms(question)
    targets = tag_targets(question)
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
        coverage = term_coverage(terms, searchable(row))
        # Coverage (share of question words present) is absolute; bm25 only breaks ties.
        score = coverage + TAG_BOOST * len(matched) / max(len(targets), 1) + 0.1 * text_scores.get(record_id, 0.0) / top
        if not matched and coverage == 0:
            continue
        for c in BOOL_COLUMNS:
            row[c] = None if row[c] is None else bool(row[c])
        ranked.append({**(public_view(row) if public_only else row), "score": round(score, 3), "matched_tags": matched,
                       "term_coverage": round(coverage, 2)})
    ranked.sort(key=lambda r: (-r["score"], r["record_id"]))
    return ranked[:limit]
