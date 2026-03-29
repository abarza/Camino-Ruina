"""Daemon que actualiza el overlay text del stream cada 30 segundos.

Consulta DFHack para obtener SITE y REGION, y escribe una línea
legible a /tmp/stream_overlay.txt. ffmpeg lo lee con drawtext reload=1.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

OVERLAY_PATH = Path(os.getenv("STREAM_OVERLAY_PATH", "/tmp/stream_overlay.txt"))
INTERVAL = int(os.getenv("STREAM_OVERLAY_INTERVAL", "30"))


def get_overlay_text() -> str:
    """Consulta DFHack + pantalla visual y devuelve el texto para el overlay."""
    state = ""
    try:
        from scripts.dfhack_io import get_game_state
        state = get_game_state()
    except Exception:
        return "Camino a la Ruina"

    site = ""
    region = ""
    date = ""
    for line in state.splitlines():
        if line.startswith("SITE: "):
            site = line[6:].strip()
        elif line.startswith("REGION: "):
            region = line[8:].strip()
        elif line.startswith("DATE: "):
            date = line[6:].strip()

    # Preferir site, fallback a region.
    location = site or region or "explorando"

    # Leer barra de estado visual para vitales.
    status = ""
    try:
        from scripts.tmux_io import TmuxTarget, capture_pane
        screen = capture_pane(TmuxTarget.from_env(), lines=3)
        # Buscar indicadores en la barra de estado.
        indicators = []
        screen_lower = screen.lower()
        if "drowsy" in screen_lower or "tired" in screen_lower:
            indicators.append("Drowsy")
        if "hungthir" in screen_lower or "hungdhyd" in screen_lower:
            indicators.append("HungThir")
        elif "hung" in screen_lower:
            indicators.append("Hungry")
        elif "thir" in screen_lower or "dhyd" in screen_lower:
            indicators.append("Thirsty")
        if "nauseous" in screen_lower:
            indicators.append("Nauseous")
        if "stunned" in screen_lower:
            indicators.append("Stunned")
        if indicators:
            status = " — " + " ".join(indicators)
    except Exception:
        pass

    parts = [f"Gonzalo — {location}"]
    if date:
        parts.append(f"Day {date}")
    if status:
        parts.append(status)

    return "  ".join(parts)


def main() -> None:
    # Escribir overlay inicial.
    OVERLAY_PATH.write_text("Camino a la Ruina\n", encoding="utf-8")

    while True:
        try:
            text = get_overlay_text()
            # Escritura atómica: escribir a tmp y renombrar.
            tmp = OVERLAY_PATH.with_suffix(".tmp")
            tmp.write_text(text + "\n", encoding="utf-8")
            tmp.rename(OVERLAY_PATH)
        except Exception:
            pass  # No crashear el daemon por errores transitorios.
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
