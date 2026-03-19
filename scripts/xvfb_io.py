"""IO para DF corriendo en Xvfb (SDL2): screenshots y envío de teclas via xdotool."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _display() -> str:
    return os.getenv("DISPLAY", ":99")


def capture_screenshot(dest: str | Path = "/tmp/df_screen.png") -> Path:
    """Captura screenshot del framebuffer Xvfb como PNG."""
    dest = Path(dest)
    subprocess.run(
        ["import", "-window", "root", str(dest)],
        env={**os.environ, "DISPLAY": _display()},
        check=True,
        capture_output=True,
    )
    return dest


def send_key(key: str) -> None:
    """Envía una tecla a la ventana DF via xdotool."""
    subprocess.run(
        ["xdotool", "key", "--clearmodifiers", key],
        env={**os.environ, "DISPLAY": _display()},
        check=False,
        capture_output=True,
    )


def send_keys(keys: list[str], delay_ms: int = 50) -> None:
    """Envía una secuencia de teclas con delay entre ellas."""
    for k in keys:
        send_key(k)
        if delay_ms > 0:
            import time
            time.sleep(delay_ms / 1000)
