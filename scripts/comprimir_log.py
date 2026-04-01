"""Pre-procesador de logs: comprime un log diario para el narrador.

Uso:
    python3 -m scripts.comprimir_log              # comprime log de hoy
    python3 -m scripts.comprimir_log 2026-03-29   # fecha específica

Genera: mundo/logs/YYYY-MM-DD.comprimido.md
No modifica el log original.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


class Cat(Enum):
    RUIDO = auto()
    MENU_AUTO = auto()
    EXPLORACION = auto()
    CONVERSACION = auto()
    COMBATE = auto()
    NECESIDAD = auto()
    EVENTO = auto()
    OTRO = auto()


@dataclass
class Turno:
    hora: str
    pantalla: str
    contexto: str
    decision: str
    teclas: str
    resultado: str
    # Campos extraídos de pantalla:
    unit: str = ""
    pos: str = ""
    hp: str = ""
    hunger: str = ""
    thirst: str = ""
    sleep: str = ""
    wounds: str = ""
    date_game: str = ""
    focus: str = ""
    region: str = ""
    nearby: str = ""
    screen: str = ""
    status_bar: str = ""
    categoria: Cat = Cat.OTRO


# ---------------------------------------------------------------------------
# Parseo
# ---------------------------------------------------------------------------

def _extraer_campo(texto: str, campo: str) -> str:
    m = re.search(rf"^{campo}:\s*(.+)$", texto, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _extraer_screen(texto: str) -> str:
    """Extrae el bloque SCREEN: del texto de pantalla."""
    m = re.search(r"\nSCREEN:\n(.*?)(?:\n```|$)", texto, re.DOTALL)
    return m.group(1).strip() if m else ""


def _extraer_status_bar(texto: str) -> str:
    m = re.search(r"\nSTATUS_BAR:\n(.*?)(?:\n```|$)", texto, re.DOTALL)
    return m.group(1).strip() if m else ""


def parsear_turnos(texto: str) -> list[Turno]:
    partes = re.split(r"(?=^## Turno )", texto, flags=re.MULTILINE)
    turnos: list[Turno] = []

    for parte in partes:
        if not parte.startswith("## Turno"):
            continue

        # Hora
        m_hora = re.match(r"## Turno (\d{1,2}:\d{2})", parte)
        hora = m_hora.group(1) if m_hora else "??:??"

        # Contexto
        m_ctx = re.search(r"\*\*Contexto:\*\*\s*(.+)", parte)
        contexto = m_ctx.group(1).strip() if m_ctx else ""

        # Decisión
        m_dec = re.search(r"\*\*Decisión:\*\*\s*(.+)", parte)
        decision = m_dec.group(1).strip() if m_dec else ""

        # Teclas
        m_tec = re.search(r"\*\*Teclas:\*\*\s*(.+)", parte)
        teclas = m_tec.group(1).strip() if m_tec else ""

        # Pantalla y Resultado (bloques ```text ... ```)
        bloques = re.findall(r"```text\n(.*?)```", parte, re.DOTALL)
        pantalla = bloques[0].strip() if len(bloques) > 0 else ""
        resultado = bloques[1].strip() if len(bloques) > 1 else ""

        t = Turno(
            hora=hora,
            pantalla=pantalla,
            contexto=contexto,
            decision=decision,
            teclas=teclas,
            resultado=resultado,
        )

        # Extraer campos estructurados de pantalla.
        t.unit = _extraer_campo(pantalla, "UNIT")
        t.pos = _extraer_campo(pantalla, "POS")
        t.hp = _extraer_campo(pantalla, "HP")
        t.hunger = _extraer_campo(pantalla, "HUNGER")
        t.thirst = _extraer_campo(pantalla, "THIRST")
        t.sleep = _extraer_campo(pantalla, "SLEEP")
        t.wounds = _extraer_campo(pantalla, "WOUNDS")
        t.date_game = _extraer_campo(pantalla, "DATE")
        t.focus = _extraer_campo(pantalla, "FOCUS")
        t.region = _extraer_campo(pantalla, "REGION")
        t.nearby = _extraer_campo(pantalla, "NEARBY")
        t.screen = _extraer_screen(pantalla)
        t.status_bar = _extraer_status_bar(pantalla)

        turnos.append(t)

    return turnos


# ---------------------------------------------------------------------------
# Clasificación
# ---------------------------------------------------------------------------

_RUIDO_FOCUS = ("title", "movieplayer", "loadgame")
_COMBATE_WORDS = ("atacar", "huir", "combate", "herido", "muerto")
_NECESIDAD_WORDS = ("comer", "beber", "dormir", "necesidad")
_EXPLORACION_DECISIONS = (
    "explorar_norte", "explorar_sur", "explorar_este", "explorar_oeste",
    "mirar_alrededor", "buscar_area", "hablar_npc", "esperar",
    "avanzar_mensajes", "ver_rastros", "cerrar conversación",
    "cerrar menú", "seleccionar",
)
_EVENTO_MESSAGES = (
    "you have discovered", "regain consciousness", "you are now",
    "you have been struck", "attacked", "you feel",
)


def clasificar(t: Turno) -> Cat:
    dec_lower = t.decision.lower()
    focus_lower = t.focus.lower()

    # Ruido: sin aventurero o title/movieplayer/loadgame
    if "(aventurero no encontrado)" in t.unit or any(f in focus_lower for f in _RUIDO_FOCUS):
        return Cat.RUIDO

    # Combate
    if any(w in dec_lower for w in _COMBATE_WORDS):
        return Cat.COMBATE

    # Necesidad
    if any(w in dec_lower for w in _NECESIDAD_WORDS):
        return Cat.NECESIDAD

    # Conversación real: solo cuando hay ConversationSpeak (diálogo de temas)
    if "conversación" in t.contexto.lower() or "conversacion" in t.contexto.lower():
        if "ConversationSpeak" in t.focus:
            return Cat.CONVERSACION
        # ConversationAddress sin diálogo real, o cerrar conversación → exploración noise
        return Cat.EXPLORACION

    # Evento: mensajes especiales en status_bar o cambio de región
    status_lower = t.status_bar.lower()
    if any(msg in status_lower for msg in _EVENTO_MESSAGES):
        return Cat.EVENTO

    # Exploración
    if any(e in dec_lower for e in _EXPLORACION_DECISIONS) or "bloqueado" in dec_lower:
        return Cat.EXPLORACION

    return Cat.OTRO


# ---------------------------------------------------------------------------
# Agrupación en corridas
# ---------------------------------------------------------------------------

@dataclass
class Corrida:
    categoria: Cat
    turnos: list[Turno] = field(default_factory=list)

    @property
    def es_comprimible(self) -> bool:
        return self.categoria in (Cat.RUIDO, Cat.MENU_AUTO, Cat.EXPLORACION) and len(self.turnos) >= 3


def agrupar_corridas(turnos: list[Turno]) -> list[Corrida]:
    if not turnos:
        return []

    corridas: list[Corrida] = []
    actual = Corrida(categoria=turnos[0].categoria, turnos=[turnos[0]])

    for t in turnos[1:]:
        # Misma categoría → extender corrida (para EXPLORACION, agrupar sub-tipos)
        if t.categoria == actual.categoria:
            actual.turnos.append(t)
        else:
            corridas.append(actual)
            actual = Corrida(categoria=t.categoria, turnos=[t])

    corridas.append(actual)
    return corridas


# ---------------------------------------------------------------------------
# Compresión
# ---------------------------------------------------------------------------

def _extraer_pos_tuple(pos: str) -> tuple[int, int, int] | None:
    m = re.search(r"x=(\d+)\s+y=(\d+)\s+z=(\d+)", pos)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None


def _comprimir_nearby(nearby: str) -> str:
    """Deduplica entidades sin nombre: '4 CRUNDLE' en vez de listar 4 veces."""
    if not nearby or nearby == "(nadie cerca)" or nearby == "(sin nombre)":
        return nearby

    conteo: dict[str, int] = {}
    nombres: list[str] = []

    for ent in re.split(r";\s*", nearby):
        ent = ent.strip()
        if not ent:
            continue
        # Quitar distancia
        ent_clean = re.sub(r",?\s*d=\d+", "", ent).strip().rstrip(",").strip()
        if "(sin nombre)" in ent:
            # Extraer tipo: "(sin nombre) (CRUNDLE, d=14)" → "CRUNDLE"
            # El formato es: "(sin nombre) (TIPO, d=N)"
            partes_paren = re.findall(r"\(([^)]+)\)", ent)
            tipo = "?"
            for p in partes_paren:
                p_clean = p.split(",")[0].strip()
                if p_clean != "sin nombre":
                    tipo = p_clean
                    break
            conteo[tipo] = conteo.get(tipo, 0) + 1
        else:
            # NPC con nombre: "Staddat Lesnoamec (HUMAN, d=3)" → "Staddat Lesnoamec (HUMAN)"
            nombres.append(ent_clean)

    partes: list[str] = []
    partes.extend(nombres)
    for tipo, n in sorted(conteo.items()):
        if n > 1:
            partes.append(f"{n}x {tipo}")
        else:
            partes.append(tipo)

    return "; ".join(partes) if partes else "(nadie cerca)"


def _limpiar_screen(screen: str) -> str:
    """Extrae solo el contenido significativo del SCREEN (diálogos, menús).

    Elimina: ASCII art, direcciones (NE, SW...), coordenadas, mapas visuales.
    """
    lineas_utiles: list[str] = []
    for line in screen.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Saltar líneas de dirección pura (NW, ESE, NNW, etc.)
        if re.fullmatch(r"[*\s]*[NESW]{1,3}", stripped):
            continue
        # Saltar Date:
        if stripped.startswith("Date:"):
            continue
        # Saltar líneas que son solo ASCII art (mapas visuales)
        if re.fullmatch(r"[.,`'@XU\s;:0!%~\[\]#\-\\/_|]+", stripped):
            continue
        # Saltar nombres de personaje en barra de status
        if stripped.startswith("Gonzalo Usuknol"):
            continue
        if stripped.startswith("The Hills") or stripped.startswith("Speed "):
            continue
        if stripped.startswith("Tracks Visible"):
            continue
        lineas_utiles.append(stripped)

    return "\n".join(lineas_utiles)


def _limpiar_turno_completo(t: Turno) -> str:
    """Genera representación limpia de un turno preservado."""
    lineas: list[str] = [f"## {t.hora} — {t.decision}"]

    # Estado compacto en una línea
    estado_parts: list[str] = []
    if t.unit:
        estado_parts.append(t.unit)
    if t.pos:
        estado_parts.append(f"POS: {t.pos}")
    if t.hp:
        estado_parts.append(f"HP: {t.hp}")
    if t.hunger:
        estado_parts.append(f"HUNGER: {t.hunger}")
    if t.thirst:
        estado_parts.append(f"THIRST: {t.thirst}")
    if t.region:
        estado_parts.append(f"REGION: {t.region}")
    if estado_parts:
        lineas.append(" | ".join(estado_parts))

    nearby_c = _comprimir_nearby(t.nearby)
    if nearby_c and nearby_c != "(nadie cerca)":
        lineas.append(f"NEARBY: {nearby_c}")

    # SCREEN content (diálogo) — preservar solo texto relevante
    if t.screen:
        screen_limpio = _limpiar_screen(t.screen)
        if screen_limpio:
            lineas.append(f"SCREEN:\n{screen_limpio}")

    # Mensajes relevantes del status_bar
    if t.status_bar:
        for line in t.status_bar.splitlines():
            ll = line.strip().lower()
            if any(msg in ll for msg in _EVENTO_MESSAGES):
                lineas.append(f"MSG: {line.strip()}")

    lineas.append("")
    return "\n".join(lineas)


def _comprimir_corrida(corrida: Corrida) -> str:
    """Genera resumen compacto de una corrida comprimible."""
    turnos = corrida.turnos
    cat = corrida.categoria
    n = len(turnos)
    h_inicio = turnos[0].hora
    h_fin = turnos[-1].hora

    if cat == Cat.RUIDO:
        return f"[{h_inicio}-{h_fin}: {n} turnos de pantalla de título/carga — omitidos]\n"

    if cat == Cat.MENU_AUTO:
        # Extraer tipos de menú
        tipos = set()
        for t in turnos:
            if t.focus:
                tipos.add(t.focus.split("/")[-1] if "/" in t.focus else t.focus)
        tipos_str = ", ".join(sorted(tipos)) if tipos else "menú"
        return f"[{h_inicio}-{h_fin}: {n} turnos de menú automático ({tipos_str}) — omitidos]\n"

    if cat == Cat.EXPLORACION:
        # Extraer direcciones, pos inicial/final, NPCs encontrados
        direcciones: dict[str, int] = {}
        for t in turnos:
            dec = t.decision.lower()
            for d in ("norte", "sur", "este", "oeste"):
                if d in dec:
                    direcciones[d] = direcciones.get(d, 0) + 1
            if "mirar" in dec:
                direcciones["mirar"] = direcciones.get("mirar", 0) + 1
            if "buscar" in dec:
                direcciones["buscar"] = direcciones.get("buscar", 0) + 1

        pos_inicio = _extraer_pos_tuple(turnos[0].pos)
        pos_fin = _extraer_pos_tuple(turnos[-1].pos)

        acciones = ", ".join(f"{k} x{v}" for k, v in sorted(direcciones.items(), key=lambda x: -x[1]))

        # NPCs encontrados durante la corrida
        npcs_vistos: set[str] = set()
        for t in turnos:
            if t.nearby and t.nearby != "(nadie cerca)":
                for ent in re.split(r";\s*", t.nearby):
                    if "(sin nombre)" not in ent and ent.strip():
                        nombre = ent.split("(")[0].strip()
                        if nombre:
                            npcs_vistos.add(nombre)

        lineas = [f"## Exploración {h_inicio}-{h_fin} ({n} turnos)"]
        lineas.append(f"Acciones: {acciones}")
        if pos_inicio and pos_fin:
            lineas.append(f"POS: ({pos_inicio[0]},{pos_inicio[1]}) → ({pos_fin[0]},{pos_fin[1]})")
        if turnos[-1].region:
            lineas.append(f"REGION: {turnos[-1].region}")
        if npcs_vistos:
            lineas.append(f"NPCs cerca: {', '.join(sorted(npcs_vistos))}")

        # Detectar cambios notables durante la corrida
        regiones = set(t.region for t in turnos if t.region)
        if len(regiones) > 1:
            lineas.append(f"Cambio de región: {' → '.join(sorted(regiones))}")

        lineas.append("")
        return "\n".join(lineas)

    # Fallback
    return f"[{h_inicio}-{h_fin}: {n} turnos ({cat.name}) — resumidos]\n"


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def comprimir(texto: str) -> str:
    turnos = parsear_turnos(texto)
    if not turnos:
        return texto

    # Clasificar
    for t in turnos:
        t.categoria = clasificar(t)

    # Agrupar en corridas
    corridas = agrupar_corridas(turnos)

    # Stats
    total_turnos = len(turnos)
    regiones = set(t.region for t in turnos if t.region)
    npcs_nombrados: set[str] = set()
    for t in turnos:
        if t.nearby and t.nearby != "(nadie cerca)":
            for ent in re.split(r";\s*", t.nearby):
                if "(sin nombre)" not in ent and ent.strip():
                    nombre = ent.split("(")[0].strip()
                    if nombre:
                        npcs_nombrados.add(nombre)

    horas = [t.hora for t in turnos]
    h_min = horas[0] if horas else "?"
    h_max = horas[-1] if horas else "?"

    # Generar output
    lineas: list[str] = []

    # Header
    lineas.append(f"# Resumen del día")
    lineas.append(f"Turnos originales: {total_turnos} | Horas: {h_min}-{h_max}")
    if regiones:
        lineas.append(f"Lugares: {', '.join(sorted(regiones))}")
    if npcs_nombrados:
        lineas.append(f"Personajes: {', '.join(sorted(npcs_nombrados))}")
    lineas.append("")

    bloques_emitidos = 0
    for corrida in corridas:
        if corrida.es_comprimible:
            lineas.append(_comprimir_corrida(corrida))
            bloques_emitidos += 1
        else:
            # Emitir cada turno individualmente
            for t in corrida.turnos:
                lineas.append(_limpiar_turno_completo(t))
                bloques_emitidos += 1

    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def mundo_dir() -> Path:
    return Path(os.getenv("MUNDO_DIR", "mundo")).resolve()


def main() -> int:
    mundo = mundo_dir()
    logs_dir = mundo / "logs"

    if len(sys.argv) > 1:
        fecha = sys.argv[1].strip()
    else:
        import datetime as dt
        fecha = dt.date.today().isoformat()

    input_path = logs_dir / f"{fecha}.md"
    output_path = logs_dir / f"{fecha}.comprimido.md"

    if not input_path.exists():
        print(f"[comprimir] Log no encontrado: {input_path}", file=sys.stderr)
        return 1

    # Idempotencia: verificar hash
    contenido_original = input_path.read_text(encoding="utf-8")
    hash_original = hashlib.md5(contenido_original.encode()).hexdigest()

    if output_path.exists():
        primera_linea = output_path.read_text(encoding="utf-8").split("\n", 1)[0]
        if f"<!-- hash:{hash_original} -->" in primera_linea:
            print(f"[comprimir] {output_path.name} ya está actualizado.")
            return 0

    # Comprimir
    resultado = comprimir(contenido_original)

    # Escribir con hash
    output_path.write_text(
        f"<!-- hash:{hash_original} -->\n{resultado}",
        encoding="utf-8",
    )

    # Stats
    lineas_original = contenido_original.count("\n")
    lineas_resultado = resultado.count("\n")
    ratio = (1 - lineas_resultado / max(lineas_original, 1)) * 100
    print(f"[comprimir] {input_path.name}: {lineas_original} → {lineas_resultado} líneas ({ratio:.0f}% reducción)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
