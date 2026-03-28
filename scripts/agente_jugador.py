from __future__ import annotations

import datetime as dt
import os
import time
from dataclasses import dataclass
from pathlib import Path

from scripts.tmux_io import TmuxTarget, send_raw_keys

USE_LLM_INTENTIONS = os.getenv("USE_LLM_INTENTIONS", "0") == "1"


@dataclass(frozen=True)
class Turno:
    hora: str
    pantalla: str
    contexto: str
    decision: str
    teclas: str
    resultado: str


def mundo_dir() -> Path:
    return Path(os.getenv("MUNDO_DIR", "mundo")).resolve()


def log_path_for_today(mundo: Path) -> Path:
    today = dt.date.today().isoformat()
    return mundo / "logs" / f"{today}.md"


def escribir_turno(path: Path, t: Turno) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"## Turno {t.hora}\n\n")
        f.write(f"**Pantalla:**\n\n```text\n{t.pantalla}\n```\n\n")
        f.write(f"**Contexto:** {t.contexto}\n")
        f.write(f"**Decisión:** {t.decision}\n")
        f.write(f"**Teclas:** {t.teclas}\n\n")
        f.write(f"**Resultado:**\n\n```text\n{t.resultado}\n```\n\n")


def detectar_contexto(pantalla: str) -> str:
    s = pantalla.lower()
    if "combat" in s or "attack" in s:
        return "combate"
    if "say" in s or "talk" in s or "conversation" in s:
        return "conversación"
    if "inventory" in s:
        return "inventario"
    return "exploración"


def delay_por_contexto(contexto: str) -> float:
    return {
        "exploración": 2.5,
        "combate": 0.8,
        "conversación": 7.0,
        "inventario": 0.4,
    }.get(contexto, 2.5)


def parse_teclas_env() -> list[str]:
    """
    Secuencia de teclas para el agente v0.

    Por defecto usa: "KP_8,KP_8,KP_6,KP_6,."
    (numpad: arriba, arriba, derecha, derecha; '.' suele ser wait en muchos roguelikes,
    y sirve como "no-op" si no aplica).
    """
    raw = os.getenv("AGENT_KEYS", "KP_8,KP_8,KP_6,KP_6,.").strip()
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


def _get_game_state() -> str:
    """Intenta obtener estado via DFHack; si falla, retorna string vacío."""
    try:
        from scripts.dfhack_io import get_game_state
        return get_game_state()
    except Exception:
        return ""


def main() -> int:
    mundo = mundo_dir()

    intervalo = float(os.getenv("AGENT_TICK_SECONDS", "10"))
    teclas = parse_teclas_env()

    while True:
        log_path = log_path_for_today(mundo)

        # Capturar estado antes de actuar.
        antes = _get_game_state()
        contexto = detectar_contexto(antes)
        decision = "Ejecutar secuencia mecánica v0"
        teclas_a_enviar = teclas

        # Si hay un menú/diálogo abierto, cerrarlo antes de decidir.
        if "FOCUS:" in antes and "dungeonmode/Default" not in antes:
            decision = "Auto: cerrar menú/diálogo (Escape)"
            teclas_a_enviar = ["Escape"]
        elif USE_LLM_INTENTIONS:
            try:
                from scripts.decisor_llm import EstadoMinimo, decidir_intencion

                intencion = decidir_intencion(EstadoMinimo(pantalla=antes, contexto=contexto))
                decision = f"Intención LLM: {intencion.nombre}"
                teclas_a_enviar = intencion.teclas
            except Exception as exc:
                import sys
                print(f"[agente] decisor LLM falló: {exc}", file=sys.stderr)
                teclas_a_enviar = teclas

        target = TmuxTarget.from_env()
        send_raw_keys(target, teclas_a_enviar)
        time.sleep(delay_por_contexto(contexto))

        # Capturar estado después de actuar.
        despues = _get_game_state()
        hora = dt.datetime.now().strftime("%H:%M")

        escribir_turno(
            log_path,
            Turno(
                hora=hora,
                pantalla=antes,
                contexto=contexto,
                decision=decision,
                teclas=",".join(teclas_a_enviar) if teclas_a_enviar else "(vacío)",
                resultado=despues,
            ),
        )

        time.sleep(intervalo)


if __name__ == "__main__":
    raise SystemExit(main())

