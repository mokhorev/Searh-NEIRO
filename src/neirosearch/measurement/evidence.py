from __future__ import annotations

import json
import os
import re
from datetime import datetime
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
    stable_id,
    utc_now,
)


def sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def safe_segment(value: str, fallback: str = "item") -> str:
    value = value.strip().casefold().replace("ё", "е")
    value = re.sub(r"[^\w\-]+", "_", value, flags=re.UNICODE)
    return re.sub(r"_+", "_", value).strip("_") or fallback


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            return
        raise FileExistsError(f"Immutable evidence already exists with different content: {path}")
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
    clean_answer = answer_text.strip() + "\n"
    sources_text = json.dumps(citations, ensure_ascii=False, indent=2) + "\n"
    answer_hash = sha256_text(clean_answer)
    capture_payload = json.dumps(
        {
            "answer_sha256": answer_hash,
            "citations": citations,
            "extra_metadata": extra_metadata,
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    capture_hash = sha256_text(capture_payload)
    destination = (
        Path(root)
        / safe_segment(company.company_id)
        / safe_segment(task.run_id)
        / safe_segment(task.provider_id)
        / safe_segment(query.query_id)
        / f"attempt_{task.attempt:02d}"
        / f"capture_{capture_hash[:12]}"
    )
    destination.mkdir(parents=True, exist_ok=True)

    answer_path = destination / "answer.md"
    sources_path = destination / "sources.json"
    metadata_path = destination / "metadata.json"

    if metadata_path.exists():
        existing_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        captured_at = datetime.fromisoformat(existing_metadata["captured_at"])
    else:
        captured_at = utc_now()

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
        "captured_at": captured_at.isoformat(),
        "answer_sha256": answer_hash,
        "capture_sha256": capture_hash,
        "extra_metadata": extra_metadata,
    }
    metadata_text = json.dumps(metadata, ensure_ascii=False, indent=2, default=str) + "\n"

    atomic_write_text(answer_path, clean_answer)
    atomic_write_text(sources_path, sources_text)
    atomic_write_text(metadata_path, metadata_text)

    answer_file_hash = sha256_text(clean_answer)
    sources_file_hash = sha256_text(sources_text)
    metadata_file_hash = sha256_text(metadata_text)
    captured = CapturedAnswer(
        answer_id=stable_id("answer", task.task_id),
        task_id=task.task_id,
        text=answer_text,
        citations=citations,
        captured_at=captured_at,
        answer_sha256=answer_hash,
        metadata={"evidence_dir": str(destination), "capture_sha256": capture_hash},
    )
    items = [
        EvidenceItem(
            evidence_id=stable_id(
                "evidence", task.task_id, EvidenceKind.ANSWER.value, capture_hash
            ),
            task_id=task.task_id,
            kind=EvidenceKind.ANSWER,
            path_or_url=str(answer_path),
            sha256=answer_file_hash,
            captured_at=captured_at,
        ),
        EvidenceItem(
            evidence_id=stable_id(
                "evidence", task.task_id, EvidenceKind.SOURCES.value, capture_hash
            ),
            task_id=task.task_id,
            kind=EvidenceKind.SOURCES,
            path_or_url=str(sources_path),
            sha256=sources_file_hash,
            captured_at=captured_at,
        ),
        EvidenceItem(
            evidence_id=stable_id(
                "evidence", task.task_id, EvidenceKind.METADATA.value, capture_hash
            ),
            task_id=task.task_id,
            kind=EvidenceKind.METADATA,
            path_or_url=str(metadata_path),
            sha256=metadata_file_hash,
            captured_at=captured_at,
        ),
    ]
    return captured, items
