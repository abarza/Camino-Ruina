from __future__ import annotations

import os
from dataclasses import dataclass


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


def completar(*, system: str, user: str, max_tokens: int = 900) -> str:
    cfg = load_config()
    if not cfg.api_key:
        raise RuntimeError("No hay API key configurada para el proveedor LLM.")

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
        # anthropic content es lista de bloques
        parts: list[str] = []
        for b in r.content:
            text = getattr(b, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()

    raise RuntimeError(f"Proveedor LLM no soportado: {cfg.provider}")

