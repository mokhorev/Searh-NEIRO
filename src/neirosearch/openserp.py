from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import requests

CSV_SEP = ";"
DEFAULT_OPENSERP_BASE_URL = "http://127.0.0.1:7000"
DEFAULT_OPENSERP_ENGINES = "google,yandex,bing,duckduckgo"


def slugify(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value.strip().lower())
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_") or "company"


def normalize_domain(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = parsed.netloc or parsed.path
    host = host.casefold().strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def openserp_search(
    query: str,
    engines: str = DEFAULT_OPENSERP_ENGINES,
    limit: int = 10,
    lang: str = "RU",
    region: str = "RU",
    timeout: int = 45,
    base_url: str | None = None,
    mode: str = "balanced",
    extract: int | bool = 0,
) -> dict[str, Any]:
    """Call a local OpenSERP instance.

    OpenSERP is optional. It is useful as the search/source layer before LLM probing.
    This client uses only a user-controlled local endpoint and does not configure proxy pools.
    """
    resolved_base_url = (base_url or os.getenv("OPENSERP_BASE_URL", DEFAULT_OPENSERP_BASE_URL)).rstrip("/")
    response = requests.get(
        f"{resolved_base_url}/mega/search",
        params={
            "engines": engines,
            "text": query,
            "limit": limit,
            "lang": lang,
            "region": region,
            "mode": mode,
            "dedupe": "true",
            "merge": "true",
            "extract": extract,
            "format": "json",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def build_company_search_queries(brand: str, industry: str = "", region: str = "") -> list[str]:
    brand = brand.strip()
    industry = industry.strip()
    region = region.strip()
    queries = [
        " ".join(part for part in [brand, industry, region] if part),
        " ".join(part for part in [brand, region, "отзывы"] if part),
        " ".join(part for part in [industry, region, "лучшие компании"] if part),
        " ".join(part for part in [industry, region, "рейтинг"] if part),
        " ".join(part for part in [industry, region, "2ГИС"] if part),
        " ".join(part for part in [industry, region, "Яндекс Карты"] if part),
    ]
    result: list[str] = []
    seen: set[str] = set()
    for query in queries:
        query = re.sub(r"\s+", " ", query).strip()
        if not query:
            continue
        key = query.casefold()
        if key not in seen:
            result.append(query)
            seen.add(key)
    return result


def flatten_openserp_results(payload: dict[str, Any], query: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in payload.get("results", []) or []:
        position = item.get("position") or {}
        extracted = item.get("extracted") or {}
        url = str(item.get("url") or "")
        domain = str(item.get("domain") or "") or normalize_domain(url)
        rows.append(
            {
                "query": query,
                "engine": item.get("engine", ""),
                "rank": item.get("rank", ""),
                "position": position.get("absolute", item.get("rank", "")),
                "type": item.get("type", ""),
                "title": item.get("title", ""),
                "url": url,
                "display_url": item.get("display_url", ""),
                "domain": normalize_domain(domain),
                "snippet": item.get("snippet", ""),
                "extracted_title": extracted.get("title", ""),
                "extracted_content": extracted.get("content", ""),
            }
        )
    return rows


def run_company_footprint_scan(
    brand: str,
    industry: str = "",
    region: str = "",
    queries: list[str] | None = None,
    engines: str = DEFAULT_OPENSERP_ENGINES,
    limit: int = 10,
    lang: str = "RU",
    region_code: str = "RU",
    timeout: int = 45,
    base_url: str | None = None,
    mode: str = "balanced",
    extract: int | bool = 0,
) -> pd.DataFrame:
    search_queries = queries or build_company_search_queries(brand, industry=industry, region=region)
    rows: list[dict[str, Any]] = []
    for query in search_queries:
        payload = openserp_search(
            query=query,
            engines=engines,
            limit=limit,
            lang=lang,
            region=region_code,
            timeout=timeout,
            base_url=base_url,
            mode=mode,
            extract=extract,
        )
        rows.extend(flatten_openserp_results(payload, query=query))
    return pd.DataFrame(
        rows,
        columns=[
            "query",
            "engine",
            "rank",
            "position",
            "type",
            "title",
            "url",
            "display_url",
            "domain",
            "snippet",
            "extracted_title",
            "extracted_content",
        ],
    )


def save_serp_results(df: pd.DataFrame, brand: str, output_root: Path = Path("outputs/serp")) -> Path:
    output_dir = output_root / slugify(brand)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "serp_results.csv"
    df.to_csv(path, sep=CSV_SEP, index=False, encoding="utf-8-sig")
    return path
