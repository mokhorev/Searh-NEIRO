from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def stable_id(prefix: str, *parts: object, length: int = 24) -> str:
    payload = "\x1f".join(str(part).strip() for part in parts)
    digest = sha256(payload.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"


class IntentClass(str, Enum):
    COMMERCIAL = "COMMERCIAL_INTENT"
    SCENARIO = "SCENARIO_INTENT"
    COMPARISON = "COMPARISON_INTENT"
    BRAND = "BRAND_INTENT"
    ENTITY_CHECK = "ENTITY_CHECK"


class CaptureMode(str, Enum):
    API = "api"
    MANUAL_WEB = "manual_web"
    ASSISTED_BROWSER = "assisted_browser"
    IMPORTED = "imported"


class WebMode(str, Enum):
    ON = "web_on"
    OFF = "web_off"
    UNKNOWN = "unknown"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    CAPTURED = "CAPTURED"
    NORMALIZED = "NORMALIZED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    STALE = "STALE"


class SignalLevel(str, Enum):
    RAW_SIGNAL = "RAW_SIGNAL"
    CROSS_SYSTEM_SIGNAL = "CROSS_SYSTEM_SIGNAL"
    REPEATED_SIGNAL = "REPEATED_SIGNAL"
    SOURCE_CONFIRMED = "SOURCE_CONFIRMED"
    CLIENT_CONFIRMED = "CLIENT_CONFIRMED"
    REJECTED = "REJECTED"
    STALE = "STALE"


class ErrorCode(str, Enum):
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    INPUT_NOT_FOUND = "INPUT_NOT_FOUND"
    SEND_FAILED = "SEND_FAILED"
    ANSWER_NOT_FOUND = "ANSWER_NOT_FOUND"
    ANSWER_INCOMPLETE = "ANSWER_INCOMPLETE"
    RATE_LIMITED = "RATE_LIMITED"
    CAPTCHA_SHOWN = "CAPTCHA_SHOWN"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    CSV_PARSE_ERROR = "CSV_PARSE_ERROR"
    PROVIDER_UI_CHANGED = "PROVIDER_UI_CHANGED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNKNOWN = "UNKNOWN"


class EvidenceKind(str, Enum):
    ANSWER = "answer"
    METADATA = "metadata"
    SCREENSHOT = "screenshot"
    SOURCES = "sources"
    DOM_EXCERPT = "dom_excerpt"
    MANUAL_NOTE = "manual_note"


class VerificationStatus(str, Enum):
    RAW_AI_CLAIM = "raw_ai_claim"
    SOURCE_SEEN = "source_seen"
    CROSS_MODEL_REPEAT = "cross_model_repeat"
    MANUALLY_VERIFIED = "manually_verified"
    CLIENT_CONFIRMED = "client_confirmed"
    REJECTED = "rejected"
    STALE = "stale"


class NVBaseModel(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True, use_enum_values=False)


class CompanyRecord(NVBaseModel):
    company_id: str
    brand: str
    industry: str = ""
    region: str = ""
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("company_id", "brand")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be empty")
        return value.strip()


class QueryRecord(NVBaseModel):
    query_id: str
    company_id: str
    prompt_id: str = ""
    prompt: str
    intent_class: IntentClass = IntentClass.SCENARIO
    critical: bool = False
    needs_repeat: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class MeasurementRun(NVBaseModel):
    run_id: str
    company_id: str
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MeasurementTask(NVBaseModel):
    task_id: str = Field(default_factory=lambda: f"task_{uuid4().hex}")
    run_id: str
    query_id: str
    provider_id: str
    provider_label: str = ""
    model: str = ""
    attempt: int = Field(default=1, ge=1)
    capture_mode: CaptureMode = CaptureMode.IMPORTED
    web_mode: WebMode = WebMode.UNKNOWN
    geo: str = ""
    personalization: str = "unknown"
    session_id: str = ""
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: ErrorCode | None = None
    error_message: str = ""
    raw_path: str = ""
    evidence_path: str = ""
    answer_sha256: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CapturedAnswer(NVBaseModel):
    answer_id: str = Field(default_factory=lambda: f"answer_{uuid4().hex}")
    task_id: str
    text: str
    citations: list[str] = Field(default_factory=list)
    captured_at: datetime = Field(default_factory=utc_now)
    answer_sha256: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def answer_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("answer text must not be empty")
        return value.strip()


class EvidenceSpan(NVBaseModel):
    label: str
    quote: str
    start: int | None = None
    end: int | None = None


class AnswerObservation(NVBaseModel):
    task_id: str
    client_mentioned: bool = False
    client_recommended: bool = False
    mention_context: str = ""
    recommendation_strength: str = "absent"
    recommendation_rank: int | None = None
    competitors_mentioned: list[str] = Field(default_factory=list)
    competitors_recommended: list[str] = Field(default_factory=list)
    candidate_entities: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    commercial_widget: str = "none"
    marketplace_capture: bool = False
    answer_classes: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    signal_level: SignalLevel = SignalLevel.RAW_SIGNAL
    requires_manual_review: bool = True
    analyzer_version: str = "measurement-core-v1"
    created_at: datetime = Field(default_factory=utc_now)


class EvidenceItem(NVBaseModel):
    evidence_id: str = Field(default_factory=lambda: f"evidence_{uuid4().hex}")
    task_id: str
    kind: EvidenceKind
    path_or_url: str
    sha256: str = ""
    captured_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryEvent(NVBaseModel):
    event_id: str = Field(default_factory=lambda: f"memory_{uuid4().hex}")
    project_id: str
    company_id: str
    source_type: str
    model: str = ""
    query: str = ""
    raw_path: str = ""
    extracted_facts: list[str] = Field(default_factory=list)
    mentioned_companies: list[str] = Field(default_factory=list)
    mentioned_competitors: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    verification_status: VerificationStatus = VerificationStatus.RAW_AI_CLAIM
    next_question: str = ""
    next_action: str = ""
    occurred_at: datetime = Field(default_factory=utc_now)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    supersedes_event_id: str | None = None
