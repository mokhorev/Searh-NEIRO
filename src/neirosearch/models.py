from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ProviderResult:
    provider_id: str
    provider_label: str
    model: str
    prompt: str
    ok: bool
    answer: str = ""
    error: str | None = None
    citations: list[str] = field(default_factory=list)
    search_results: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AnswerAnalysis:
    brand: str
    brand_found: bool
    brand_position: int | None
    competitors_found: list[str]
    role: str
    confidence: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
