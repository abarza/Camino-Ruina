from __future__ import annotations

import datetime as dt
import os
import re
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


def _parsear_int(state: str, key: str, default: int = 0) -> int:
    """Extrae un valor numérico del estado: 'HUNGER: 42000' → 42000."""
    m = re.search(rf"{key}\s*(\d+)", state)
    return int(m.group(1)) if m else default


def _extraer_pos(state: str) -> str:
    """Extrae 'x=N y=N z=N' del estado."""
    m = re.search(r"POS: (x=\d+ y=\d+ z=\d+)", state)
    return m.group(1) if m else ""


def detectar_contexto(state: str) -> str:
    """Detecta contexto basándose en FOCUS de DFHack (no en regex de texto)."""
    if "FOCUS:" not in state:
        return "exploración"

    focus = ""
    for line in state.splitlines():
        if line.startswith("FOCUS: "):
            focus = line[7:].strip()
            break

    if "Conversation" in focus:
        return "conversación"
    if focus != "dungeonmode/Default" and focus != "unknown":
        return "menú"

    # Pantalla normal: revisar necesidades urgentes.
    hunger = _parsear_int(state, "HUNGER:")
    thirst = _parsear_int(state, "THIRST:")
    sleep = _parsear_int(state, "SLEEP:")
    if sleep > 40000 or hunger > 50000 or thirst > 40000:
        return "necesidad"

    return "exploración"


def delay_por_contexto(contexto: str) -> float:
    return {
        "exploración": 2.5,
        "combate": 0.8,
        "conversación": 3.0,
        "inventario": 0.4,
        "necesidad": 1.0,
        "menú": 0.5,
    }.get(contexto, 2.5)


def parse_teclas_env() -> list[str]:
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


def _cerrar_menu() -> None:
    """Cierra menú/diálogo via DFHack LEAVESCREEN (más confiable que tmux Escape)."""
    try:
        from scripts.dfhack_io import simulate_input
        simulate_input("LEAVESCREEN")
    except Exception:
        pass


def main() -> int:
    mundo = mundo_dir()

    intervalo = float(os.getenv("AGENT_TICK_SECONDS", "10"))
    teclas = parse_teclas_env()
    pos_anterior = ""
    ticks_atascado = 0

    while True:
        log_path = log_path_for_today(mundo)

        # Capturar estado antes de actuar.
        antes = _get_game_state()
        contexto = detectar_contexto(antes)
        decision = "Ejecutar secuencia mecánica v0"
        teclas_a_enviar = teclas

        # Detectar si está atascado (misma posición varios ticks).
        pos_actual = _extraer_pos(antes)
        if pos_actual and pos_actual == pos_anterior:
            ticks_atascado += 1
        else:
            ticks_atascado = 0
        pos_anterior = pos_actual

        # Si hay un menú abierto (no conversación), cerrar via DFHack.
        if contexto == "menú":
            _cerrar_menu()
            decision = "Auto: cerrar menú (LEAVESCREEN)"
            teclas_a_enviar = []
        elif contexto == "conversación":
            # Capturar pantalla visual para ver opciones de conversación.
            pantalla_visual = ""
            try:
                from scripts.tmux_io import TmuxTarget, capture_pane
                pantalla_visual = capture_pane(TmuxTarget.from_env(), lines=30)
            except Exception:
                pass

            if pantalla_visual:
                antes += "\n\nSCREEN:\n" + pantalla_visual

            # Por ahora cerrar — TODO: LLM elige opción del menú.
            _cerrar_menu()
            decision = "Auto: cerrar conversación (LEAVESCREEN)"
            teclas_a_enviar = []
        elif USE_LLM_INTENTIONS:
            try:
                from scripts.decisor_llm import EstadoMinimo, decidir_intencion

                intencion = decidir_intencion(
                    EstadoMinimo(
                        pantalla=antes,
                        contexto=contexto,
                        ticks_atascado=ticks_atascado,
                    )
                )
                decision = f"Intención LLM: {intencion.nombre}"
                teclas_a_enviar = intencion.teclas
            except Exception as exc:
                import sys
                print(f"[agente] decisor LLM falló: {exc}", file=sys.stderr)
                teclas_a_enviar = teclas

        target = TmuxTarget.from_env()
        if teclas_a_enviar:
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
                teclas=",".join(teclas_a_enviar) if teclas_a_enviar else "(DFHack)",
                resultado=despues,
            ),
        )

        time.sleep(intervalo)


if __name__ == "__main__":
    raise SystemExit(main())
