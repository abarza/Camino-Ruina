from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass

_CONTEXT_WINDOWS: dict[str, int] = {
    "gpt-4o-mini": 128_000,
    "gpt-4o": 128_000,
    "gpt-4.1-mini": 1_000_000,
    "gpt-4.1-nano": 1_000_000,
    "gpt-5.4-mini": 400_000,
    "gpt-5.2": 400_000,
    "claude-3-5-sonnet-latest": 200_000,
    "claude-sonnet-4-5-20250514": 200_000,
    "claude-3-5-haiku-latest": 200_000,
}

_DEFAULT_CONTEXT = 100_000
_RETRY_DELAY = 30
_MAX_RETRIES = 1


@dataclass(frozen=True)
class LlmConfig:
    provider: str
    model: str
    api_key: str | None


def load_config() -> LlmConfig:
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if provider == "anthropic":
        return LlmConfig(
            provider="anthropic",
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
            api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        )
    return LlmConfig(
        provider="openai",
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY") or None,
    )


def context_window(model: str) -> int:
    return _CONTEXT_WINDOWS.get(model, _DEFAULT_CONTEXT)


def completar(*, system: str, user: str, max_tokens: int = 900) -> str:
    cfg = load_config()
    if not cfg.api_key:
        raise RuntimeError("No hay API key configurada para el proveedor LLM.")

    last_err: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return _llamar_llm(cfg, system=system, user=user, max_tokens=max_tokens)
        except Exception as e:
            last_err = e
            if attempt < _MAX_RETRIES:
                print(
                    f"[llm] Intento {attempt + 1} falló ({e}), "
                    f"reintentando en {_RETRY_DELAY}s...",
                    file=sys.stderr,
                )
                time.sleep(_RETRY_DELAY)
    raise last_err  # type: ignore[misc]


def _llamar_llm(
    cfg: LlmConfig, *, system: str, user: str, max_tokens: int,
) -> str:
    if cfg.provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=cfg.api_key)
        r = client.chat.completions.create(
            model=cfg.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=0.9,
        )
        return (r.choices[0].message.content or "").strip()

    if cfg.provider == "anthropic":
        from anthropic import Anthropic

        client = Anthropic(api_key=cfg.api_key)
        r = client.messages.create(
            model=cfg.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts: list[str] = []
        for b in r.content:
            text = getattr(b, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()

    raise RuntimeError(f"Proveedor LLM no soportado: {cfg.provider}")

