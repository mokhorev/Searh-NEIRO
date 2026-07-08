from __future__ import annotations

import os
from typing import Any

import requests


def openserp_search(
    query: str,
    engines: str = "yandex,bing,duckduckgo,google",
    limit: int = 10,
    lang: str = "RU",
    region: str = "RU",
    timeout: int = 45,
) -> dict[str, Any]:
    """Call a local OpenSERP instance if OPENSERP_BASE_URL is configured.

    OpenSERP is optional. It is useful as the search/source layer before LLM probing.
    """
    base_url = os.getenv("OPENSERP_BASE_URL", "http://127.0.0.1:7000").rstrip("/")
    response = requests.get(
        f"{base_url}/mega/search",
        params={
            "engines": engines,
            "text": query,
            "limit": limit,
            "lang": lang,
            "region": region,
            "format": "json",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
