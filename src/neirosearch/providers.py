from __future__ import annotations

import os
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

import requests
from openai import OpenAI

from .models import ProviderResult


class Provider(ABC):
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        self.provider_id = str(cfg["id"])
        self.label = str(cfg.get("label", self.provider_id))
        self.model = resolve_cfg_value(cfg, "model") or ""

    @abstractmethod
    def ask(self, prompt: str, system: str | None = None, timeout: int = 90) -> ProviderResult:
        raise NotImplementedError


def resolve_cfg_value(cfg: dict[str, Any], key: str, default: str | None = None) -> str | None:
    env_key = cfg.get(f"{key}_env")
    if env_key:
        return os.getenv(str(env_key), default)
    value = cfg.get(key, default)
    if value is None:
        return default
    return str(value)


def env_value(cfg: dict[str, Any], env_key_name: str, default: str | None = None) -> str | None:
    env_name = cfg.get(env_key_name)
    if not env_name:
        return default
    return os.getenv(str(env_name), default)


def is_configured(cfg: dict[str, Any]) -> tuple[bool, str | None]:
    provider_type = cfg.get("type")
    if not cfg.get("enabled", True):
        return False, "disabled in config"
    if provider_type == "ollama":
        return True, None
    if provider_type == "gigachat":
        auth_key = env_value(cfg, "auth_key_env")
        return (bool(auth_key), None if auth_key else f"missing ${cfg.get('auth_key_env')}")
    if provider_type == "yandexgpt":
        api_key = env_value(cfg, "api_key_env")
        folder_id = env_value(cfg, "folder_id_env")
        if not api_key:
            return False, f"missing ${cfg.get('api_key_env')}"
        if not folder_id:
            return False, f"missing ${cfg.get('folder_id_env')}"
        return True, None
    if provider_type in {"openai_compatible", "anthropic", "perplexity"}:
        explicit_key = cfg.get("api_key")
        api_key = env_value(cfg, "api_key_env") or explicit_key
        base_url = resolve_cfg_value(cfg, "base_url")
        model = resolve_cfg_value(cfg, "model")
        if provider_type == "openai_compatible" and not base_url:
            return False, "missing base_url"
        if not model:
            return False, "missing model"
        if not api_key:
            return False, f"missing ${cfg.get('api_key_env')}"
        return True, None
    return False, f"unsupported provider type: {provider_type}"


def make_result(
    provider: Provider,
    prompt: str,
    ok: bool,
    answer: str = "",
    error: str | None = None,
    start_time: float | None = None,
    citations: list[str] | None = None,
    search_results: list[dict[str, Any]] | None = None,
    raw: dict[str, Any] | None = None,
) -> ProviderResult:
    latency_ms = None
    if start_time is not None:
        latency_ms = int((time.time() - start_time) * 1000)
    return ProviderResult(
        provider_id=provider.provider_id,
        provider_label=provider.label,
        model=provider.model,
        prompt=prompt,
        ok=ok,
        answer=answer,
        error=error,
        citations=citations or [],
        search_results=search_results or [],
        latency_ms=latency_ms,
        raw=raw or {},
    )


class OpenAICompatibleProvider(Provider):
    def ask(self, prompt: str, system: str | None = None, timeout: int = 90) -> ProviderResult:
        start = time.time()
        api_key = env_value(self.cfg, "api_key_env") or str(self.cfg.get("api_key", ""))
        base_url = resolve_cfg_value(self.cfg, "base_url")
        model = resolve_cfg_value(self.cfg, "model") or self.model
        self.model = model
        try:
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=model, messages=messages)
            answer = response.choices[0].message.content or ""
            raw = response.model_dump() if hasattr(response, "model_dump") else {}
            return make_result(self, prompt, True, answer=answer, start_time=start, raw=raw)
        except Exception as exc:  # noqa: BLE001
            return make_result(self, prompt, False, error=str(exc), start_time=start)


class GigaChatProvider(Provider):
    token_cache: dict[str, tuple[str, float]] = {}

    def _access_token(self, timeout: int) -> str:
        auth_key = env_value(self.cfg, "auth_key_env")
        if not auth_key:
            raise RuntimeError(f"Missing ${self.cfg.get('auth_key_env')}")
        scope = os.getenv(str(self.cfg.get("scope_env", "GIGACHAT_SCOPE")), "GIGACHAT_API_PERS")
        cache_key = f"{auth_key}:{scope}"
        cached = self.token_cache.get(cache_key)
        now = time.time()
        if cached and cached[1] > now + 60:
            return cached[0]
        response = requests.post(
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "RqUID": str(uuid.uuid4()),
                "Authorization": f"Basic {auth_key}",
            },
            data={"scope": scope},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload["access_token"]
        expires_at_ms = payload.get("expires_at")
        expires_at = (expires_at_ms / 1000) if expires_at_ms else now + 29 * 60
        self.token_cache[cache_key] = (token, expires_at)
        return token

    def ask(self, prompt: str, system: str | None = None, timeout: int = 90) -> ProviderResult:
        start = time.time()
        verify_ssl = os.getenv("GIGACHAT_VERIFY_SSL", "true").lower() not in {"0", "false", "no"}
        try:
            token = self._access_token(timeout=timeout)
            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = requests.post(
                "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"model": self.model, "messages": messages},
                timeout=timeout,
                verify=verify_ssl,
            )
            response.raise_for_status()
            payload = response.json()
            answer = payload["choices"][0]["message"]["content"]
            return make_result(self, prompt, True, answer=answer, start_time=start, raw=payload)
        except Exception as exc:  # noqa: BLE001
            return make_result(self, prompt, False, error=str(exc), start_time=start)


class YandexGPTProvider(Provider):
    def ask(self, prompt: str, system: str | None = None, timeout: int = 90) -> ProviderResult:
        start = time.time()
        api_key = env_value(self.cfg, "api_key_env")
        folder_id = env_value(self.cfg, "folder_id_env")
        model = resolve_cfg_value(self.cfg, "model") or self.model
        self.model = model
        try:
            if not api_key or not folder_id:
                raise RuntimeError("YANDEX_API_KEY and YANDEX_FOLDER_ID are required")
            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "text": system})
            messages.append({"role": "user", "text": prompt})
            response = requests.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                headers={"Authorization": f"Api-Key {api_key}", "Content-Type": "application/json"},
                json={
                    "modelUri": f"gpt://{folder_id}/{model}",
                    "completionOptions": {"stream": False, "temperature": 0.2, "maxTokens": 2000},
                    "messages": messages,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            answer = payload["result"]["alternatives"][0]["message"]["text"]
            return make_result(self, prompt, True, answer=answer, start_time=start, raw=payload)
        except Exception as exc:  # noqa: BLE001
            return make_result(self, prompt, False, error=str(exc), start_time=start)


class AnthropicProvider(Provider):
    def ask(self, prompt: str, system: str | None = None, timeout: int = 90) -> ProviderResult:
        start = time.time()
        api_key = env_value(self.cfg, "api_key_env")
        try:
            if not api_key:
                raise RuntimeError(f"Missing ${self.cfg.get('api_key_env')}")
            payload: dict[str, Any] = {
                "model": self.model,
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                payload["system"] = system
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            parts = data.get("content", [])
            answer = "\n".join(part.get("text", "") for part in parts if part.get("type") == "text")
            return make_result(self, prompt, True, answer=answer, start_time=start, raw=data)
        except Exception as exc:  # noqa: BLE001
            return make_result(self, prompt, False, error=str(exc), start_time=start)


class PerplexityProvider(Provider):
    def ask(self, prompt: str, system: str | None = None, timeout: int = 90) -> ProviderResult:
        start = time.time()
        api_key = env_value(self.cfg, "api_key_env")
        try:
            if not api_key:
                raise RuntimeError(f"Missing ${self.cfg.get('api_key_env')}")
            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = requests.post(
                "https://api.perplexity.ai/v1/sonar",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "messages": messages},
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            answer = data["choices"][0]["message"].get("content", "")
            citations = data.get("citations") or []
            search_results = data.get("search_results") or []
            return make_result(
                self,
                prompt,
                True,
                answer=answer,
                citations=citations,
                search_results=search_results,
                start_time=start,
                raw=data,
            )
        except Exception as exc:  # noqa: BLE001
            return make_result(self, prompt, False, error=str(exc), start_time=start)


class OllamaProvider(Provider):
    def ask(self, prompt: str, system: str | None = None, timeout: int = 90) -> ProviderResult:
        start = time.time()
        base_url = resolve_cfg_value(self.cfg, "base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = requests.post(
                f"{base_url.rstrip('/')}/api/chat",
                json={"model": self.model, "messages": messages, "stream": False},
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            answer = data.get("message", {}).get("content", "")
            return make_result(self, prompt, True, answer=answer, start_time=start, raw=data)
        except Exception as exc:  # noqa: BLE001
            return make_result(self, prompt, False, error=str(exc), start_time=start)


def build_provider(cfg: dict[str, Any]) -> Provider:
    provider_type = cfg.get("type")
    if provider_type == "openai_compatible":
        return OpenAICompatibleProvider(cfg)
    if provider_type == "gigachat":
        return GigaChatProvider(cfg)
    if provider_type == "yandexgpt":
        return YandexGPTProvider(cfg)
    if provider_type == "anthropic":
        return AnthropicProvider(cfg)
    if provider_type == "perplexity":
        return PerplexityProvider(cfg)
    if provider_type == "ollama":
        return OllamaProvider(cfg)
    raise ValueError(f"Unsupported provider type: {provider_type}")
