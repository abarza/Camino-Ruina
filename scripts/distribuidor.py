"""Distribuidor de crónicas: Ghost → Telegram + Twitter + Resend.

Se ejecuta después del narrador nocturno. Extrae el último episodio
de la maleta activa y lo publica en todos los canales configurados.
Cada canal es independiente — si uno falla, los demás siguen.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import jwt
import requests


def mundo_dir() -> Path:
    return Path(os.getenv("MUNDO_DIR", "mundo")).resolve()


def extraer_ultimo_episodio(maleta_path: Path) -> tuple[str, str]:
    """Extrae el último episodio de la maleta (entre los dos últimos '---').

    Retorna (titulo, episodio). Ignora bloques de error/stub.
    """
    if not maleta_path.exists():
        return "", ""
    texto = maleta_path.read_text(encoding="utf-8")
    bloques = texto.split("\n---\n")

    # Buscar el último bloque que sea un episodio real (no error/stub).
    for bloque in reversed(bloques):
        bloque = bloque.strip()
        if not bloque:
            continue
        if bloque.startswith("ERROR LLM:"):
            continue
        if "(Narrador en modo stub:" in bloque:
            continue
        if "(El narrador corrió sin logs:" in bloque:
            continue
        if bloque.startswith("# Maleta"):
            continue

        # Extraer título del encabezado (primera línea).
        lineas = bloque.splitlines()
        titulo = lineas[0].strip() if lineas else "Crónica de Gonzalo"
        return titulo, bloque

    return "", ""


# --- Ghost ---


def _ghost_jwt(api_key: str) -> str:
    """Genera JWT para Ghost Admin API desde la key formato 'id:secret'."""
    kid, secret_hex = api_key.split(":")
    secret = bytes.fromhex(secret_hex)
    now = int(time.time())
    payload = {"iat": now, "exp": now + 300, "aud": "/admin/"}
    return jwt.encode(payload, secret, algorithm="HS256", headers={"kid": kid})


def publicar_ghost(episodio: str, titulo: str) -> str | None:
    """Publica el episodio en Ghost. Retorna la URL del post o None."""
    ghost_url = os.getenv("GHOST_URL", "").rstrip("/")
    api_key = os.getenv("GHOST_ADMIN_API_KEY", "")
    if not ghost_url or not api_key:
        print("[distribuidor] GHOST_URL o GHOST_ADMIN_API_KEY no configuradas, saltando Ghost.", file=sys.stderr)
        return None

    token = _ghost_jwt(api_key)

    # Ghost espera mobiledoc. Convertimos el texto plano a un card de markdown.
    mobiledoc = json.dumps({
        "version": "0.3.1",
        "markups": [],
        "atoms": [],
        "cards": [["markdown", {"markdown": episodio}]],
        "sections": [[10, 0]],
    })

    r = requests.post(
        f"{ghost_url}/ghost/api/admin/posts/",
        headers={
            "Authorization": f"Ghost {token}",
            "Content-Type": "application/json",
        },
        json={"posts": [{"title": titulo, "mobiledoc": mobiledoc, "status": "published"}]},
        timeout=30,
    )
    r.raise_for_status()
    post = r.json()["posts"][0]
    url = post.get("url", "")
    print(f"[distribuidor] Ghost: publicado → {url}")
    return url


# --- Telegram ---


def publicar_telegram(episodio: str, url_ghost: str | None) -> None:
    """Envía el episodio al canal de Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHANNEL_ID", "")
    if not token or not chat_id:
        print("[distribuidor] TELEGRAM no configurado, saltando.", file=sys.stderr)
        return

    texto = episodio
    if url_ghost:
        texto += f"\n\n🔗 {url_ghost}"

    # Telegram max 4096 chars.
    if len(texto) > 4096:
        texto = texto[:4090] + "\n[...]"

    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"},
        timeout=30,
    )
    if r.ok:
        print(f"[distribuidor] Telegram: enviado a {chat_id}")
    else:
        print(f"[distribuidor] Telegram error: {r.status_code} {r.text}", file=sys.stderr)


# --- Twitter/X ---


def publicar_twitter(episodio: str, url_ghost: str | None) -> None:
    """Publica extracto + link en Twitter/X."""
    api_key = os.getenv("TWITTER_API_KEY", "")
    api_secret = os.getenv("TWITTER_API_SECRET", "")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN", "")
    access_secret = os.getenv("TWITTER_ACCESS_SECRET", "")

    if not all([api_key, api_secret, access_token, access_secret]):
        print("[distribuidor] TWITTER no configurado, saltando.", file=sys.stderr)
        return

    import tweepy

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )

    # Primer párrafo como extracto, truncado a ~200 chars.
    parrafos = [p.strip() for p in episodio.split("\n\n") if p.strip()]
    # Saltar el encabezado "Maleta N — Día N — lugar".
    extracto = parrafos[1] if len(parrafos) > 1 else parrafos[0] if parrafos else ""
    max_len = 250 if url_ghost else 275
    if len(extracto) > max_len:
        extracto = extracto[: max_len - 3] + "..."

    tweet = extracto
    if url_ghost:
        tweet += f"\n\n{url_ghost}"

    r = client.create_tweet(text=tweet)
    print(f"[distribuidor] Twitter: publicado (id={r.data['id']})")



# --- Main ---


def main() -> int:
    mundo = mundo_dir()
    maleta_path = mundo / "maletas" / "maleta_001.md"

    titulo, episodio = extraer_ultimo_episodio(maleta_path)
    if not episodio:
        print("[distribuidor] No hay episodio nuevo para distribuir.", file=sys.stderr)
        return 0

    print(f"[distribuidor] Episodio: {titulo[:60]}...")

    # 1. Ghost primero (para obtener URL).
    url_ghost: str | None = None
    try:
        url_ghost = publicar_ghost(episodio, titulo)
    except Exception as e:
        print(f"[distribuidor] Ghost falló: {e}", file=sys.stderr)

    # 2. Telegram y Twitter (independientes).
    try:
        publicar_telegram(episodio, url_ghost)
    except Exception as e:
        print(f"[distribuidor] Telegram falló: {e}", file=sys.stderr)

    try:
        publicar_twitter(episodio, url_ghost)
    except Exception as e:
        print(f"[distribuidor] Twitter falló: {e}", file=sys.stderr)

    # Newsletter: Ghost lo maneja nativamente via Resend SMTP.
    # No necesitamos enviar email desde aquí.

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
