from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .analyzer import result_record, summarize_results
from .models import ProviderResult


def ensure_output_dir(path: str | Path) -> Path:
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_jsonl(results: list[ProviderResult], output_dir: Path, brand: str, competitors: list[str]) -> Path:
    path = output_dir / "results.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for result in results:
            fh.write(json.dumps(result_record(result, brand, competitors), ensure_ascii=False) + "\n")
    return path


def write_csv(results: list[ProviderResult], output_dir: Path, brand: str, competitors: list[str]) -> Path:
    path = output_dir / "summary.csv"
    fieldnames = [
        "provider_id",
        "provider_label",
        "model",
        "ok",
        "brand_found",
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
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            record = result_record(result, brand, competitors)
            analysis: dict[str, Any] | None = record.get("analysis")
            writer.writerow(
                {
                    "provider_id": result.provider_id,
                    "provider_label": result.provider_label,
                    "model": result.model,
                    "ok": result.ok,
                    "brand_found": analysis.get("brand_found") if analysis else "",
                    "brand_position": analysis.get("brand_position") if analysis else "",
                    "role": analysis.get("role") if analysis else "",
                    "competitors_found": ", ".join(analysis.get("competitors_found", [])) if analysis else "",
                    "latency_ms": result.latency_ms,
                    "error": result.error or "",
                    "prompt": result.prompt,
                    "answer": result.answer,
                    "citations": ", ".join(result.citations),
                }
            )
    return path


def write_markdown(results: list[ProviderResult], output_dir: Path, brand: str, competitors: list[str]) -> Path:
    path = output_dir / "report.md"
    summary = summarize_results(results, brand, competitors)
    lines = [
        f"# AI visibility report: {brand}",
        "",
        f"- Total answers: {summary['total_results']}",
        f"- Successful answers: {summary['ok_results']}",
        f"- Brand found: {summary['brand_found']}",
        f"- Brand recommended: {summary['brand_recommended']}",
        f"- Visibility rate: {summary['visibility_rate']}",
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
                    f"**Brand position:** {analysis['brand_position']}",
                    f"**Role:** {analysis['role']}",
                    f"**Competitors found:** {', '.join(analysis['competitors_found']) or '-'}",
                ]
            )
        if result.citations:
            lines.append(f"**Citations:** {', '.join(result.citations)}")
        lines.extend(["", "**Answer:**", "", result.answer or "_No answer_", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_all_reports(results: list[ProviderResult], output_dir: str | Path, brand: str, competitors: list[str]) -> list[Path]:
    out = ensure_output_dir(output_dir)
    return [
        write_jsonl(results, out, brand, competitors),
        write_csv(results, out, brand, competitors),
        write_markdown(results, out, brand, competitors),
    ]
