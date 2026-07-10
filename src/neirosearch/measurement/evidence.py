from __future__ import annotations

import json
import os
import re
from hashlib import sha256
from pathlib import Path
from typing import Any

from .models import (
    CapturedAnswer,
    CompanyRecord,
    EvidenceItem,
    EvidenceKind,
    MeasurementTask,
    QueryRecord,
)


def sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def safe_segment(value: str, fallback: str = "item") -> str:
    value = value.strip().casefold().replace("ё", "е")
    value = re.sub(r"[^\w\-]+", "_", value, flags=re.UNICODE)
    return re.sub(r"_+", "_", value).strip("_") or fallback


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def write_answer_evidence(
    *,
    root: str | Path,
    company: CompanyRecord,
    query: QueryRecord,
    task: MeasurementTask,
    answer_text: str,
    citations: list[str] | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> tuple[CapturedAnswer, list[EvidenceItem]]:
    citations = citations or []
    extra_metadata = extra_metadata or {}
    answer_hash = sha256_text(answer_text)
    destination = (
        Path(root)
        / safe_segment(company.company_id)
        / safe_segment(task.run_id)
        / safe_segment(task.provider_id)
        / safe_segment(query.query_id)
        / f"attempt_{task.attempt:02d}"
    )
    destination.mkdir(parents=True, exist_ok=True)

    answer_path = destination / "answer.md"
    sources_path = destination / "sources.json"
    metadata_path = destination / "metadata.json"

    atomic_write_text(answer_path, answer_text.strip() + "\n")
    atomic_write_text(sources_path, json.dumps(citations, ensure_ascii=False, indent=2) + "\n")

    metadata = {
        "company_id": company.company_id,
        "brand": company.brand,
        "query_id": query.query_id,
        "prompt_id": query.prompt_id,
        "prompt": query.prompt,
        "intent_class": query.intent_class.value,
        "task_id": task.task_id,
        "run_id": task.run_id,
        "provider_id": task.provider_id,
        "provider_label": task.provider_label,
        "model": task.model,
        "attempt": task.attempt,
        "capture_mode": task.capture_mode.value,
        "web_mode": task.web_mode.value,
        "geo": task.geo,
        "personalization": task.personalization,
        "session_id": task.session_id,
        "answer_sha256": answer_hash,
        **extra_metadata,
    }
    metadata_text = json.dumps(metadata, ensure_ascii=False, indent=2, default=str) + "\n"
    atomic_write_text(metadata_path, metadata_text)

    captured = CapturedAnswer(
        task_id=task.task_id,
        text=answer_text,
        citations=citations,
        answer_sha256=answer_hash,
        metadata={"evidence_dir": str(destination)},
    )
    items = [
        EvidenceItem(
            task_id=task.task_id,
            kind=EvidenceKind.ANSWER,
            path_or_url=str(answer_path),
            sha256=answer_hash,
        ),
        EvidenceItem(
            task_id=task.task_id,
            kind=EvidenceKind.SOURCES,
            path_or_url=str(sources_path),
            sha256=sha256_text(sources_path.read_text(encoding="utf-8")),
        ),
        EvidenceItem(
            task_id=task.task_id,
            kind=EvidenceKind.METADATA,
            path_or_url=str(metadata_path),
            sha256=sha256_text(metadata_path.read_text(encoding="utf-8")),
        ),
    ]
    return captured, items
