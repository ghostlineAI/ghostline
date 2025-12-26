from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.services.document_processor import DocumentProcessor


@dataclass(frozen=True)
class SourceSpec:
    path: Path
    filename: str
    optional: bool = False


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    sources: list[SourceSpec]
    generated_texts: list[Path]


def _repo_root_from_api_dir(api_dir: Path) -> Path:
    # ghostline/api → ghostline → repo root is parent of ghostline
    ghostline_dir = api_dir.parent
    return ghostline_dir.parent


def _ensure_agents_on_syspath(api_dir: Path) -> None:
    """
    Make `ghostline/agents` importable as packages `agents` and `orchestrator`.

    API poetry env doesn't install the agents project, so we add it explicitly for evals.
    """
    repo_root = _repo_root_from_api_dir(api_dir)
    agents_root = repo_root / "ghostline" / "agents"
    if agents_root.exists():
        sys.path.insert(0, str(agents_root))


def _get_chapter_subgraph():
    api_dir = Path(__file__).resolve().parents[1]  # ghostline/api
    _ensure_agents_on_syspath(api_dir)

    # Import after sys.path injection
    from orchestrator.subgraphs import ChapterSubgraph, SubgraphConfig  # type: ignore

    return ChapterSubgraph(config=SubgraphConfig())


def load_case(case_dir: Path) -> CaseSpec:
    case_path = case_dir / "case.yaml"
    raw = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid case.yaml: expected dict, got {type(raw).__name__}")

    case_id = str(raw.get("case_id") or case_dir.name)

    sources_raw = raw.get("sources") or []
    if not isinstance(sources_raw, list):
        raise ValueError("case.yaml: sources must be a list")

    sources: list[SourceSpec] = []
    for item in sources_raw:
        if not isinstance(item, dict):
            raise ValueError("case.yaml: each source must be a dict")
        p = (case_dir / str(item["path"])).resolve()
        filename = str(item.get("filename") or p.name)
        optional = bool(item.get("optional") or False)
        sources.append(SourceSpec(path=p, filename=filename, optional=optional))

    gens_raw = raw.get("generated_texts") or []
    if not isinstance(gens_raw, list) or not gens_raw:
        raise ValueError("case.yaml: generated_texts must be a non-empty list")
    generated_texts = [(case_dir / str(item["path"])).resolve() for item in gens_raw]

    return CaseSpec(case_id=case_id, sources=sources, generated_texts=generated_texts)


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff", ".bmp"}


def extract_sources(
    sources: list[SourceSpec],
    *,
    enable_vlm: bool,
) -> tuple[list[dict], list[dict]]:
    """
    Returns:
      - source_chunks_with_citations: list[{"citation": str, "content": str}]
      - source_errors: list[{"filename": str, "path": str, "error": str}]
    """
    dp = DocumentProcessor()
    chunks: list[dict] = []
    errors: list[dict] = []

    for src in sources:
        if not src.path.exists():
            if src.optional:
                continue
            raise FileNotFoundError(str(src.path))

        if _is_image(src.path) and not enable_vlm:
            # Mixed-modal cases can keep images optional for offline eval.
            errors.append(
                {
                    "filename": src.filename,
                    "path": str(src.path),
                    "error": "skipped_image_vlm_disabled",
                }
            )
            continue

        try:
            data = src.path.read_bytes()
            extracted = dp.extract_from_bytes(data, filename=src.filename)
            chunks.append({"citation": src.filename, "content": extracted.content})
        except Exception as e:  # pragma: no cover (depends on local system libs)
            if src.optional:
                errors.append(
                    {"filename": src.filename, "path": str(src.path), "error": f"{type(e).__name__}: {e}"}
                )
                continue
            raise

    return chunks, errors


def evaluate_text(
    *,
    case_id: str,
    generated_path: Path,
    content: str,
    source_chunks_with_citations: list[dict],
    source_errors: list[dict],
) -> dict[str, Any]:
    sg = _get_chapter_subgraph()

    style_issues = sg._compute_style_issues(content)
    citation_report = sg._verify_inline_citations(content, source_chunks_with_citations, project_id=None)

    word_count = len(content.split())
    heading_count = content.count("\n## ")
    em_dash_count = content.count("—") + content.count("–")

    return {
        "case_id": case_id,
        "generated_path": str(generated_path),
        "word_count": word_count,
        "heading_count": heading_count,
        "em_dash_count": em_dash_count,
        "style_issues": style_issues,
        "citation_report": citation_report,
        "source_errors": source_errors,
    }


def evaluate_case(case_dir: Path, *, enable_vlm: bool) -> list[dict[str, Any]]:
    spec = load_case(case_dir)
    source_chunks, source_errors = extract_sources(spec.sources, enable_vlm=enable_vlm)

    reports: list[dict[str, Any]] = []
    for gen_path in spec.generated_texts:
        content = gen_path.read_text(encoding="utf-8")
        reports.append(
            evaluate_text(
                case_id=spec.case_id,
                generated_path=gen_path,
                content=content,
                source_chunks_with_citations=source_chunks,
                source_errors=source_errors,
            )
        )

    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description="GhostLine local eval harness")
    parser.add_argument("--case", required=True, help="Path to a case directory containing case.yaml")
    parser.add_argument("--out", help="Optional path to write JSON results")
    parser.add_argument(
        "--enable-vlm",
        action="store_true",
        help="Enable VLM-based image extraction (may call external models)",
    )
    args = parser.parse_args()

    reports = evaluate_case(Path(args.case).resolve(), enable_vlm=bool(args.enable_vlm))
    payload = {"reports": reports}

    if args.out:
        out_path = Path(args.out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


