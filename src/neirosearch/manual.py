from __future__ import annotations

import csv
from pathlib import Path

from .models import ProviderResult

MANUAL_PROVIDERS = [
    "chatgpt_web",
    "gemini_web",
    "qwen_web",
    "gigachat_web",
    "yandexgpt_web",
    "claude_web",
    "perplexity_web",
    "deepseek_web",
    "grok_web",
    "kimi_web",
    "glm_web",
]


def write_manual_template(
    prompts: list[str],
    output_path: str | Path,
    providers: list[str] | None = None,
) -> Path:
    providers = providers or MANUAL_PROVIDERS
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "provider_id",
                "provider_label",
                "model",
                "prompt_id",
                "prompt",
                "answer",
                "citations",
                "notes",
            ],
        )
        writer.writeheader()
        for provider in providers:
            for idx, prompt in enumerate(prompts, start=1):
                writer.writerow(
                    {
                        "provider_id": provider,
                        "provider_label": provider.replace("_", " ").title(),
                        "model": "web/manual",
                        "prompt_id": idx,
                        "prompt": prompt,
                        "answer": "",
                        "citations": "",
                        "notes": "",
                    }
                )
    return path


def read_manual_answers(path: str | Path) -> list[ProviderResult]:
    results: list[ProviderResult] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            answer = (row.get("answer") or "").strip()
            if not answer:
                continue
            citations = [item.strip() for item in (row.get("citations") or "").split(",") if item.strip()]
            results.append(
                ProviderResult(
                    provider_id=row.get("provider_id") or "manual",
                    provider_label=row.get("provider_label") or row.get("provider_id") or "Manual",
                    model=row.get("model") or "web/manual",
                    prompt=row.get("prompt") or "",
                    ok=True,
                    answer=answer,
                    citations=citations,
                    raw={"prompt_id": row.get("prompt_id"), "notes": row.get("notes")},
                )
            )
    return results
