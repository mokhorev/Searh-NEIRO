from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .analyzer import result_record, summarize_results
from .models import ProviderResult

EXCEL_DELIMITER = ";"
EXCEL_FORMULA_PREFIXES = ("=", "+", "-", "@")


def ensure_output_dir(path: str | Path) -> Path:
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def excel_safe_text(value: object) -> str:
    """Prevent CSV/Excel formula execution while preserving visible text."""
    if value is None:
        return ""
    text = str(value)
    candidate = text.lstrip(" \t\r\n")
    if candidate.startswith(EXCEL_FORMULA_PREFIXES):
        return "'" + text
    return text


def write_jsonl(
    results: list[ProviderResult], output_dir: Path, brand: str, competitors: list[str]
) -> Path:
    path = output_dir / "results.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for result in results:
            record = result_record(result, brand, competitors)
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def write_csv(
    results: list[ProviderResult], output_dir: Path, brand: str, competitors: list[str]
) -> Path:
    path = output_dir / "summary.csv"
    fieldnames = [
        "provider_id",
        "provider_label",
        "model",
        "ok",
        "brand_found",
        "brand_in_prompt",
        "organic_brand_found",
        "brand_position",
        "role",
        "competitors_found",
        "latency_ms",
        "error",
        "prompt",
        "answer",
        "citations",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter=EXCEL_DELIMITER)
        writer.writeheader()
        for result in results:
            record = result_record(result, brand, competitors)
            analysis: dict[str, Any] | None = record.get("analysis")
            writer.writerow(
                {
                    "provider_id": excel_safe_text(result.provider_id),
                    "provider_label": excel_safe_text(result.provider_label),
                    "model": excel_safe_text(result.model),
                    "ok": result.ok,
                    "brand_found": analysis.get("brand_found") if analysis else "",
                    "brand_in_prompt": record.get("brand_in_prompt", ""),
                    "organic_brand_found": record.get("organic_brand_found", ""),
                    "brand_position": analysis.get("brand_position") if analysis else "",
                    "role": excel_safe_text(analysis.get("role")) if analysis else "",
                    "competitors_found": excel_safe_text(
                        ", ".join(analysis.get("competitors_found", [])) if analysis else ""
                    ),
                    "latency_ms": result.latency_ms,
                    "error": excel_safe_text(result.error or ""),
                    "prompt": excel_safe_text(result.prompt),
                    "answer": excel_safe_text(record.get("answer", "")),
                    "citations": excel_safe_text(", ".join(result.citations)),
                }
            )
    return path


def write_markdown(
    results: list[ProviderResult], output_dir: Path, brand: str, competitors: list[str]
) -> Path:
    path = output_dir / "report.md"
    summary = summarize_results(results, brand, competitors)
    lines = [
        f"# AI visibility report: {brand}",
        "",
        f"- Total answers: {summary['total_results']}",
        f"- Successful answers: {summary['ok_results']}",
        f"- Brand found: {summary['brand_found']}",
        f"- Brand found organically: {summary['organic_brand_found']} / "
        f"{summary['organic_results']}",
        f"- Brand recommended: {summary['brand_recommended']}",
        f"- Visibility rate: {summary['visibility_rate']}",
        f"- Organic visibility rate: {summary['organic_visibility_rate']}",
        f"- Recommendation rate: {summary['recommendation_rate']}",
        "",
        "## Answers",
        "",
    ]
    for index, result in enumerate(results, start=1):
        record = result_record(result, brand, competitors)
        analysis = record.get("analysis")
        lines.extend(
            [
                f"### {index}. {result.provider_label} / `{result.model}`",
                "",
                f"**Prompt:** {result.prompt}",
                "",
                f"**Status:** {'OK' if result.ok else 'ERROR'}",
            ]
        )
        if result.error:
            lines.append(f"**Error:** `{result.error}`")
        if analysis:
            lines.extend(
                [
                    f"**Brand found:** {analysis['brand_found']}",
                    f"**Brand in prompt:** {record['brand_in_prompt']}",
                    f"**Organic brand found:** {record['organic_brand_found']}",
                    f"**Brand position:** {analysis['brand_position']}",
                    f"**Role:** {analysis['role']}",
                    f"**Competitors found:** "
                    f"{', '.join(analysis['competitors_found']) or '-'}",
                ]
            )
        if result.citations:
            lines.append(f"**Citations:** {', '.join(result.citations)}")
        lines.extend(["", "**Answer:**", "", record.get("answer") or "_No answer_", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_all_reports(
    results: list[ProviderResult], output_dir: str | Path, brand: str, competitors: list[str]
) -> list[Path]:
    out = ensure_output_dir(output_dir)
    return [
        write_jsonl(results, out, brand, competitors),
        write_csv(results, out, brand, competitors),
        write_markdown(results, out, brand, competitors),
    ]
