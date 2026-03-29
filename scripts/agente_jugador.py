from __future__ import annotations

import datetime as dt
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from scripts.tmux_io import TmuxTarget, capture_pane, send_raw_keys

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

    return "exploración"


def detectar_necesidad(screen: str) -> str:
    """Lee la barra de estado visual de DF para detectar necesidades.

    Retorna: 'dormir', 'comer', 'beber', 'comer_beber', o '' si no hay necesidad.
    Solo actúa si DF lo muestra en pantalla — no adivinamos con contadores.
    Nunca come/bebe si hay estados negativos por exceso.
    """
    s = screen.lower()

    # Estados que BLOQUEAN comer/beber — esperar a que pasen.
    if any(w in s for w in (
        "really full", "starting to feel full", "nausea", "nauseous", "stunned",
        "vomit", "too much", "keep it down",
    )):
        return ""

    if "drowsy" in s or "tired" in s:
        return "dormir"
    # "Dhyd" = Dehydrated, "Thir" = Thirsty
    if "hungthir" in s or "hungdhyd" in s:
        return "comer_beber"
    if ("hung" in s and "thir" in s) or ("hung" in s and "dhyd" in s):
        return "comer_beber"
    if "hung" in s:
        return "comer"
    if "thir" in s or "dhyd" in s:
        return "beber"

    return ""


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


def _encontrar_npc_en_menu(screen: str) -> dict | None:
    """Busca un NPC real en el menú 'Who will you talk to?'.

    Retorna {"name": "...", "index": N} o None si no hay nadie.
    Las opciones no-NPC son: Begin a performance, Shout out,
    Assume an identity, y Deity.
    """
    if "who will you talk to" not in screen.lower():
        return None

    no_npc = ("begin a performance", "shout out", "assume an identity", "deity")

    # Extraer líneas después de "Who will you talk to?"
    in_options = False
    index = 0
    for line in screen.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if "who will you talk to" in stripped.lower():
            in_options = True
            continue
        if not in_options:
            continue
        # Línea de status bar = fin de opciones.
        if stripped.startswith("Gonzalo") or stripped.startswith("The Hills"):
            break
        # Saltar líneas que no son opciones.
        if stripped.startswith("Date:") or stripped.startswith("ENE") or stripped.startswith("*"):
            break

        lower = stripped.lower()
        if any(n in lower for n in no_npc):
            index += 1
            continue

        # Es un NPC real (ej: "The craftsman Thur Stoltaduthros")
        return {"name": stripped, "index": index}

    return None


def _elegir_opcion_menu(screen: str, focus: str) -> str:
    """Elige una letra de opción del menú de Eat/Drink/Sleep.

    Busca líneas tipo 'c - . echidna tripe [5]' y elige la más apropiada.
    Para Eat: preferir comida (tripe, meat, fish, plump, bread), evitar
    armas, monedas, waterskin.
    Para Drink/waterskin: elegir líquidos (ice, water, ale, wine).
    Para Sleep: elegir la primera opción disponible.
    """
    opciones: list[tuple[str, str]] = []
    for line in screen.splitlines():
        line = line.strip()
        # Formato: "c - . echidna tripe [5]" o "a - copper whip"
        m = re.match(r"^([a-z])\s*[-–]\s*\.?\s*(.+)$", line)
        if m:
            opciones.append((m.group(1), m.group(2).strip().lower()))

    if not opciones:
        return ""

    if "Sleep" in focus:
        return opciones[0][0]

    # Para Eat/Drink: filtrar por tipo.
    # Evitar armas, monedas, herramientas.
    evitar = ("whip", "knife", "coin", "sword", "axe", "shield", "helm", "boot", "gauntlet")
    # Preferir comida/bebida.
    preferir = ("tripe", "meat", "fish", "plump", "bread", "biscuit", "stew",
                "ice", "water", "ale", "wine", "beer", "mead", "waterskin", "milk")

    # Primero buscar algo preferido.
    for letra, desc in opciones:
        if any(p in desc for p in preferir):
            return letra

    # Si no, cualquiera que no sea de evitar.
    for letra, desc in opciones:
        if not any(e in desc for e in evitar):
            return letra

    # Último recurso: primera opción.
    return opciones[0][0]


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
    cooldown_hablar = 0  # ticks antes de poder hablar otra vez
    cooldown_comer = 0   # ticks antes de poder comer otra vez
    cooldown_mirar = 0   # ticks antes de poder mirar/buscar otra vez

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

        # Si hay un menú abierto (no conversación), actuar según tipo.
        if contexto == "menú":
            focus_line = ""
            for line in antes.splitlines():
                if line.startswith("FOCUS: "):
                    focus_line = line[7:].strip()
                    break

            if "Sleep" in focus_line:
                # Menú de Sleep: confirmar via DFHack SELECT.
                try:
                    from scripts.dfhack_io import simulate_input
                    simulate_input("SELECT")
                except Exception:
                    pass
                decision = "Auto: confirmar dormir (SELECT)"
                teclas_a_enviar = []
            elif any(k in focus_line for k in ("Eat", "Drink")):
                # Menú de Eat/Drink: capturar pantalla COMPLETA para ver barra de estado.
                screen = ""
                try:
                    screen = capture_pane(TmuxTarget.from_env(), lines=80)
                except Exception:
                    pass

                screen_lower = screen.lower()
                # Bloquear si hay CUALQUIER señal de exceso.
                if any(w in screen_lower for w in (
                    "really full", "starting to feel full",
                    "nausea", "nauseous", "stunned",
                    "vomit", "too much", "keep it down",
                )):
                    _cerrar_menu()
                    decision = "Auto: lleno/nausea/stunned, cerrar menú"
                    teclas_a_enviar = []
                else:
                    opcion = _elegir_opcion_menu(screen, focus_line)
                    if opcion:
                        decision = f"Auto: seleccionar '{opcion}' en {focus_line}"
                        teclas_a_enviar = [opcion]
                    else:
                        _cerrar_menu()
                        decision = f"Auto: cerrar {focus_line} (sin opciones)"
                        teclas_a_enviar = []
            else:
                _cerrar_menu()
                decision = "Auto: cerrar menú (LEAVESCREEN)"
                teclas_a_enviar = []
        elif contexto == "conversación":
            # Capturar pantalla visual para ver opciones de conversación.
            pantalla_visual = ""
            try:
                pantalla_visual = capture_pane(TmuxTarget.from_env(), lines=40)
            except Exception:
                pass

            if pantalla_visual:
                antes += "\n\nSCREEN:\n" + pantalla_visual

            npc = _encontrar_npc_en_menu(pantalla_visual)
            if npc:
                # Hay un NPC real — seleccionarlo con SELECT (primera opción).
                # Si el NPC no es la primera opción, navegar con CURSOR_DOWN.
                try:
                    from scripts.dfhack_io import simulate_input
                    for _ in range(npc["index"]):
                        simulate_input("STANDARDSCROLL_DOWN")
                        time.sleep(0.1)
                    simulate_input("SELECT")
                except Exception:
                    pass
                decision = f"Auto: hablar con {npc['name']}"
                teclas_a_enviar = []
                cooldown_hablar = 15  # cooldown más largo después de conversar
            else:
                # No hay NPC real — cerrar menú.
                _cerrar_menu()
                decision = "Auto: cerrar conversación (nadie con quien hablar)"
                teclas_a_enviar = []
                cooldown_hablar = 10
        else:
            # Pantalla normal (Default): capturar barra de estado visual.
            try:
                status_bar = capture_pane(TmuxTarget.from_env(), lines=5)
                if status_bar.strip():
                    antes += "\n\nSTATUS_BAR:\n" + status_bar
            except Exception:
                pass

            # Decrementar cooldowns.
            if cooldown_hablar > 0:
                cooldown_hablar -= 1
            if cooldown_comer > 0:
                cooldown_comer -= 1
            if cooldown_mirar > 0:
                cooldown_mirar -= 1

            # Detectar si hay estados que bloquean comer/beber.
            _bloqueado_comer = cooldown_comer > 0 or any(
                w in antes.lower()
                for w in ("nauseous", "stunned", "really full", "starting to feel full", "vomit", "too much", "keep it down")
            )

            if USE_LLM_INTENTIONS:
                try:
                    from scripts.decisor_llm import EstadoMinimo, decidir_intencion

                    intencion = decidir_intencion(
                        EstadoMinimo(
                            pantalla=antes,
                            contexto=contexto,
                            ticks_atascado=ticks_atascado,
                        )
                    )

                    # Override: bloquear acciones que causan loops.
                    if intencion.nombre == "comer_beber" and _bloqueado_comer:
                        decision = "Auto: bloqueado comer (nausea/stunned/cooldown), esperando"
                        teclas_a_enviar = ["."]
                    elif intencion.nombre == "hablar_npc" and cooldown_hablar > 0:
                        decision = f"Auto: bloqueado hablar (cooldown {cooldown_hablar}), explorando"
                        teclas_a_enviar = ["KP_6", "KP_6", "KP_6"]
                    elif intencion.nombre in ("mirar_alrededor", "buscar_area") and cooldown_mirar > 0:
                        decision = f"Auto: bloqueado mirar (cooldown {cooldown_mirar}), explorando"
                        teclas_a_enviar = ["KP_8", "KP_8", "KP_8"]
                    else:
                        decision = f"Intención LLM: {intencion.nombre}"
                        teclas_a_enviar = intencion.teclas
                        # Poner cooldowns después de acciones que abren menús.
                        if intencion.nombre == "comer_beber":
                            cooldown_comer = 10
                        elif intencion.nombre == "hablar_npc":
                            cooldown_hablar = 10
                        elif intencion.nombre in ("mirar_alrededor", "buscar_area"):
                            cooldown_mirar = 8
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
