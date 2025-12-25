#!/usr/bin/env python3
"""
Audit a generated book (Markdown) against the ingested source materials.

This is a deterministic grounding audit:
- Verifies each footnote quote exists in the referenced source filename's extracted text
- Checks paragraph -> cited-quote lexical overlap (flags likely hallucinated/embellished prose)

Usage:
  cd ghostline/api
  poetry run python scripts/audit_book_grounding.py \
    --project-id d1f106cf-5e7e-485a-8595-fcd569bf4676 \
    --book-md /Users/ageorges/Desktop/GhostLine/exports/mental_health_guide.md \
    --out-json /Users/ageorges/Desktop/GhostLine/exports/mental_health_guide.grounding_audit.json
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    # Collapse to alnum tokens for robust substring matching
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "so", "to", "of", "in", "on", "for", "with",
    "as", "at", "by", "from", "that", "this", "these", "those", "it", "its", "is", "are",
    "was", "were", "be", "been", "being", "i", "you", "we", "they", "he", "she", "them",
    "my", "your", "our", "their", "me", "him", "her", "us", "do", "does", "did", "not",
    "no", "yes", "if", "then", "than", "because", "while", "when", "what", "which", "who",
    "whom", "where", "why", "how", "can", "could", "should", "would", "may", "might",
    "will", "just", "really", "very", "also", "too",
}


def _tokenize(s: str) -> set[str]:
    toks = [t for t in _norm(s).split() if t and t not in STOPWORDS and len(t) > 2]
    return set(toks)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


@dataclass
class Footnote:
    number: int
    filename: str
    quote: str
    raw: str


def parse_footnotes(md: str) -> dict[int, Footnote]:
    # Markdown footnotes look like: [^12]: mentalhealth1.pdf - "quote"
    pattern = re.compile(r'^\[\^(\d+)\]:\s*([^\s]+)\s*-\s*"(.+?)"\s*$', re.MULTILINE)
    footnotes: dict[int, Footnote] = {}
    for m in pattern.finditer(md):
        n = int(m.group(1))
        filename = m.group(2).strip()
        quote = m.group(3).strip()
        footnotes[n] = Footnote(number=n, filename=filename, quote=quote, raw=m.group(0))
    return footnotes


def extract_paragraphs(md: str) -> list[str]:
    # Remove footnote definition lines
    md_wo_defs = re.sub(r'^\[\^\d+\]:.*$', "", md, flags=re.MULTILINE)
    # Remove title/metadata separators that are not content
    md_wo_defs = re.sub(r'^\s*---\s*$', "", md_wo_defs, flags=re.MULTILINE)
    # Keep headings as their own paragraphs (we'll ignore them later)
    paras = [p.strip() for p in re.split(r"\n\s*\n+", md_wo_defs) if p.strip()]
    return paras


def audit(
    project_id: UUID,
    book_md_path: Path,
) -> dict[str, Any]:
    from app.db.base import SessionLocal
    from app.models.source_material import SourceMaterial

    md = book_md_path.read_text(encoding="utf-8")
    footnotes = parse_footnotes(md)
    paras = extract_paragraphs(md)

    # Load sources from DB (full extracted text)
    db = SessionLocal()
    try:
        materials = (
            db.query(SourceMaterial)
            .filter(SourceMaterial.project_id == project_id)
            .all()
        )
        sources: dict[str, str] = {}
        for sm in materials:
            if not sm.filename:
                continue
            txt = sm.extracted_text or sm.extracted_content or ""
            sources[sm.filename] = txt
    finally:
        db.close()

    # Verify footnote quotes exist
    footnote_results = []
    verified = 0
    missing = 0
    missing_source = 0

    for n, fn in sorted(footnotes.items()):
        src_txt = sources.get(fn.filename)
        if not src_txt:
            missing_source += 1
            footnote_results.append(
                {
                    "number": n,
                    "filename": fn.filename,
                    "quote": fn.quote,
                    "verified": False,
                    "reason": "missing_source_text",
                }
            )
            continue

        ok = _norm(fn.quote) in _norm(src_txt)
        if ok:
            verified += 1
        else:
            missing += 1
        footnote_results.append(
            {
                "number": n,
                "filename": fn.filename,
                "quote": fn.quote,
                "verified": ok,
                "reason": None if ok else "quote_not_found_in_source",
            }
        )

    # Paragraph overlap audit
    low_overlap = []
    uncited = 0
    checked = 0

    for p in paras:
        # Ignore headings and word-count lines
        if p.startswith("#"):
            continue
        if p.lower().startswith("*word count:"):
            continue

        # Treat >=20 words as substantive
        if len(p.split()) < 20:
            continue

        checked += 1
        refs = [int(x) for x in re.findall(r"\[\^(\d+)\]", p)]
        if not refs:
            uncited += 1
            low_overlap.append(
                {
                    "reason": "no_footnotes_in_paragraph",
                    "overlap": 0.0,
                    "paragraph_preview": p[:300],
                    "refs": [],
                }
            )
            continue

        # Collect quotes for referenced footnotes
        quotes = []
        for r in refs:
            f = footnotes.get(r)
            if f:
                quotes.append(f.quote)
        quote_text = " ".join(quotes)

        ptoks = _tokenize(p)
        qtoks = _tokenize(quote_text)
        overlap = _jaccard(ptoks, qtoks)

        # Flag paragraphs that are far from the cited quotes (likely embellishment)
        if overlap < 0.08:
            low_overlap.append(
                {
                    "reason": "low_lexical_overlap_with_cited_quotes",
                    "overlap": overlap,
                    "paragraph_preview": p[:300],
                    "refs": refs,
                    "quotes_preview": quote_text[:250],
                }
            )

    report = {
        "project_id": str(project_id),
        "book_md_path": str(book_md_path),
        "sources_in_db": sorted(list(sources.keys())),
        "footnotes_found": len(footnotes),
        "footnotes_verified": verified,
        "footnotes_missing_quote": missing,
        "footnotes_missing_source": missing_source,
        "footnote_verification_rate": (verified / len(footnotes)) if footnotes else 0.0,
        "footnote_results": footnote_results,
        "paragraphs_checked": checked,
        "paragraphs_uncited": uncited,
        "low_overlap_paragraphs": low_overlap[:50],  # cap
        "low_overlap_count": len(low_overlap),
    }
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-id", required=True)
    ap.add_argument("--book-md", required=True)
    ap.add_argument("--out-json", required=False)
    args = ap.parse_args()

    project_id = UUID(args.project_id)
    book_md_path = Path(args.book_md)
    if not book_md_path.exists():
        raise SystemExit(f"Book markdown not found: {book_md_path}")

    report = audit(project_id=project_id, book_md_path=book_md_path)

    print("=== GROUNDING AUDIT SUMMARY ===")
    print(f"Book: {report['book_md_path']}")
    print(f"Footnotes: {report['footnotes_found']} (verified: {report['footnotes_verified']}, missing quote: {report['footnotes_missing_quote']}, missing source: {report['footnotes_missing_source']})")
    print(f"Footnote verification rate: {report['footnote_verification_rate']:.2%}")
    print(f"Paragraphs checked: {report['paragraphs_checked']}, uncited: {report['paragraphs_uncited']}, low-overlap flagged: {report['low_overlap_count']}")

    if report["low_overlap_paragraphs"]:
        print("\nTop flagged paragraphs (preview):")
        for i, item in enumerate(report["low_overlap_paragraphs"][:10], 1):
            print(f"\n{i}. overlap={item.get('overlap'):.3f} reason={item.get('reason')}")
            print(item.get("paragraph_preview", ""))

    if args.out_json:
        out = Path(args.out_json)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nSaved report: {out}")


if __name__ == "__main__":
    main()


