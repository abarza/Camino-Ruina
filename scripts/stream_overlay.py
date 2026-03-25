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
    """Consulta DFHack y devuelve el texto para el overlay."""
    try:
        from scripts.dfhack_io import get_game_state
        state = get_game_state()
    except Exception:
        return "Camino a la Ruina"

    site = ""
    region = ""
    for line in state.splitlines():
        if line.startswith("SITE: "):
            site = line[6:].strip()
        elif line.startswith("REGION: "):
            region = line[8:].strip()

    # Preferir site, fallback a region.
    location = site or region or "explorando"

    return f"Gonzalo — {location}"


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
