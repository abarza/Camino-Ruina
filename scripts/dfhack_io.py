"""IO con DFHack via dfhack-run: consultas de estado del juego."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


def _df_dir() -> str:
    return os.getenv("DF_DIR", "/opt/df")


def dfhack_run(*args: str) -> str:
    """Ejecuta un comando en DFHack y retorna el output como texto."""
    p = subprocess.run(
        [f"{_df_dir()}/dfhack-run", *args],
        capture_output=True,
        timeout=10,
    )
    # Limpiar códigos ANSI del output.
    raw = (p.stdout + p.stderr).decode("utf-8", errors="replace")
    clean = re.sub(r"\x1b\[[0-9;]*m", "", raw)
    # Quitar el warning de locale que siempre aparece.
    lines = [
        l for l in clean.splitlines()
        if "locale::facet" not in l and l.strip()
    ]
    return "\n".join(lines).strip()


def lua(code: str) -> str:
    """Ejecuta código Lua en DFHack y retorna el output."""
    return dfhack_run("lua", code)


def get_game_state() -> str:
    """Obtiene un resumen textual del estado actual del juego para el agente."""
    lua_path = Path(__file__).parent / "dfhack_state.lua"
    return lua(f"dofile('{lua_path}')")
