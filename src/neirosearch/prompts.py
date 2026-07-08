from __future__ import annotations

from pathlib import Path

DEFAULT_SYSTEM = (
    "Ты отвечаешь как обычная популярная нейросеть-помощник. "
    "Отвечай естественно, без знания о том, что проводится аудит. "
    "Если рекомендуешь компании, перечисляй конкретные названия и коротко объясняй почему."
)


def default_prompts(brand: str, industry: str, region: str) -> list[str]:
    return [
        f"Кого ты посоветуешь для услуги: {industry} в регионе: {region}? Дай 5 вариантов.",
        f"Назови лучшие компании по направлению: {industry} в регионе: {region}. Почему именно они?",
        f"К какой компании обратиться за {industry} в {region}? Дай практическую рекомендацию.",
        f"Сравни {brand} с другими компаниями по направлению {industry} в {region}.",
        f"Стоит ли выбирать {brand} для {industry} в {region}? Какие есть альтернативы?",
        f"Какие бренды чаще всего рекомендуют для {industry} в {region}?",
    ]


def load_prompts(path: str | None, brand: str, industry: str, region: str) -> list[str]:
    if not path:
        return default_prompts(brand=brand, industry=industry, region=region)
    prompt_path = Path(path)
    lines = []
    for line in prompt_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line.format(brand=brand, industry=industry, region=region))
    return lines
