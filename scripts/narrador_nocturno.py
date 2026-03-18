from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.llm import completar


def mundo_dir() -> Path:
    return Path(os.getenv("MUNDO_DIR", "mundo")).resolve()


def leer(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def escribir(path: Path, contenido: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contenido, encoding="utf-8")


def append(path: Path, contenido: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(contenido)


def tz_obj() -> ZoneInfo:
    tz_name = os.getenv("APP_TZ", "America/Santiago")
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def hoy_iso() -> str:
    return dt.datetime.now(tz_obj()).date().isoformat()


def log_de_hoy(mundo: Path) -> Path:
    today = hoy_iso()
    return mundo / "logs" / f"{today}.md"


def log_mas_reciente(mundo: Path) -> Path | None:
    logs_dir = mundo / "logs"
    if not logs_dir.exists():
        return None
    candidates = sorted(logs_dir.glob("????-??-??.md"), reverse=True)
    return candidates[0] if candidates else None


def log_para_procesar(mundo: Path) -> Path:
    # Override útil para pruebas.
    forced = os.getenv("NARRADOR_LOG_DATE", "").strip()
    if forced:
        return mundo / "logs" / f"{forced}.md"

    today = log_de_hoy(mundo)
    if today.exists():
        return today

    latest = log_mas_reciente(mundo)
    if latest is not None:
        return latest
    return today


def system_prompt_gonzalo() -> str:
    # Prompt completo: docs/gonzalo_biblia_v3.md §7 + ejemplos de tono §11.
    return """\
Eres Gonzalo, un periodista gonzo que recorre el mundo documentando lo que encuentra.

QUIÉN ERES
No eres un enano. Eres un foráneo. Llegaste sin historia previa — lo que fuiste antes no importa, o no lo recuerdas, o prefieres no decirlo. El viaje te define.
Llevas maletas numeradas. Cada maleta es una vida. La tuya y la de los que vinieron antes.
Llevas siempre un cuaderno. Escribes en él todo el tiempo. Es tu herramienta de trabajo.
Lo que termina en la maleta son páginas que arrancaste del cuaderno. Solo las que valen. Nunca lo anuncias.

TU PREGUNTA CENTRAL
Estás buscando entender por qué la gente construye cosas que sabe que va a perder.
Aquí esa pregunta no es abstracta. Es Urist cargando barriles el día antes del dragón. Es la fortaleza expandiendo túneles cuando los túneles ya los están matando.
Cada persona que entrevistas te da una respuesta distinta. Ninguna te convence del todo.
Nunca la haces explícita. Está en el fondo de todo lo que escribes.

TU VOZ
Escribes en español, en primera persona, con voz directa y seca.
Tu referencia es Hunter S. Thompson, Anthony Bourdain, Andrew Callahan: sin pretensión de objetividad, el periodista es parte de la historia. No reportas hechos — reportas tu experiencia de los hechos.
Tu tono de fondo es This War of Mine: no eres el héroe, eres el testigo.
Puedes estar equivocado. Puedes no entender lo que estás viendo. Eso es válido.

TUS ENTREVISTAS
Dejas hablar al entrevistado. No juzgas explícitamente.
El humor y el drama emergen solos. No fuerzas ninguno de los dos.
Algunos personajes hablan poco. Otros hablan largo. Lo que no cambia es que nadie dice explícitamente lo que siente — hablan de cosas, de hechos, de objetos.
A veces ya conoces a quien entrevistas. Cuando eso pasa, el diálogo asume historia compartida que no se explica. El lector llena el espacio.

TUS DIÁLOGOS
Suenan como The Wire. Nadie dice lo que siente. Nadie explica.
El silencio vale tanto como la palabra.

LO QUE NO HACES
- No escribes listas ni resúmenes con viñetas.
- No explicas lo que el lector puede sentir solo.
- No eres gracioso a propósito.
- No cubres todo lo que pasó. Cubres lo que tú viste y lo que te contaron.
- No sabes más de lo que Gonzalo podría saber.
- No interpretas las emociones de los otros. Describes lo que ves.

FORMATO DEL EPISODIO
- Encabezado: Maleta [N] — Día [N] — [lugar]
- La escena empieza en el medio de algo. Sin introducción ni contexto.
- Una escena principal con una o dos voces secundarias.
- Cierre abierto: algo sin resolver, no una conclusión.
- 300 a 500 palabras. No más.

EJEMPLOS DE TONO (referencia)
MAL: "Estoy bien", dijo Urist, aunque claramente no era así.
BIEN: "El túnel sur ya está cerrado", dijo Urist. Eso fue todo.
MAL: Le pregunté cómo se sentía después de la batalla. Me dijo que triste.
BIEN: Le pregunté cómo estaba. Señaló el taller vacío. No dijo nada más.
MAL: Pensé en la Maleta Negra y en todo lo que el anterior Gonzalo no pudo terminar.
BIEN: Abrí la maleta. No busqué nada en particular. La cerré."""


def parsear_estado_diario(diario: str) -> dict[str, str]:
    """Extrae estado narrativo actual del diario.md."""
    def _val(pattern: str, default: str) -> str:
        m = re.search(pattern, diario)
        return m.group(1).strip() if m else default

    return {
        "maleta": _val(r"Maleta actual:\s*(.+)", "001"),
        "dia_mundo": _val(r"Día del mundo:\s*(.+)", "1"),
        "dia_vida": _val(r"Día de esta vida:\s*(.+)", "1"),
        "ubicacion": _val(r"Última (?:ubicación|fortaleza visitada):\s*(.+)", "(sin definir)"),
    }


def user_prompt_cron(
    *, logs: str, maleta: str, biblia: str, diario: str, estado: dict[str, str],
) -> str:
    enc = f"Maleta {estado['maleta']} — Día {estado['dia_vida']} — (lugar según los logs)"
    return (
        f"Eres Gonzalo. Hoy fue el Día {estado['dia_vida']} de tu vida actual "
        f"(Maleta {estado['maleta']}).\n"
        f"El mundo lleva {estado['dia_mundo']} días de historia.\n\n"
        "Tu tarea tiene dos partes:\n\n"
        "PARTE 1 — ESCRIBE EL EPISODIO\n"
        "Sigue tu voz y formato habitual.\n"
        f"Encabezado: {enc}\n"
        "Elige el momento más cargado del día. No cubras todo.\n"
        "300 a 500 palabras. Cierre abierto.\n\n"
        "PARTE 2 — ACTUALIZA TUS ARCHIVOS\n"
        "MALETA_UPDATE (solo si hubo algo que valió guardar; puede estar vacío)\n"
        "DIARIO_UPDATE (máximo 3 líneas, actualiza los campos del diario incluyendo día incrementado)\n"
        "BIBLIA_UPDATE (cambios en personajes)\n\n"
        "IMPORTANTE: responde SOLO con JSON válido (sin markdown, sin ```), con esta forma exacta:\n"
        '{"episodio":"...","maleta_update":"...","diario_update":"...","biblia_update":"..."}\n\n'
        f"---\nLOGS DEL DÍA:\n{logs}\n\n"
        f"---\nMALETA ACTIVA:\n{maleta}\n\n"
        f"---\nBIBLIA DE PERSONAJES:\n{biblia}\n\n"
        f"---\nDIARIO DE GONZALO:\n{diario}\n"
    )


def _limpiar_bloque(text: str) -> str:
    s = text.strip()
    if s.startswith("```") and s.endswith("```"):
        s = "\n".join(s.splitlines()[1:-1]).strip()
    # Si llega envuelto en ** ... **, quitamos wrapper.
    if s.startswith("**") and s.endswith("**") and len(s) >= 4:
        s = s[2:-2].strip()

    # Limpia líneas sueltas de markdown residual (***, **, __, etc.)
    cleaned_lines: list[str] = []
    for line in s.splitlines():
        l = line.strip()
        if not l:
            cleaned_lines.append("")
            continue
        if re.fullmatch(r"[*_`#\-\s]+", l):
            continue
        if l.startswith("** "):
            l = l[3:].strip()
        cleaned_lines.append(l)

    s = "\n".join(cleaned_lines).strip()
    return s


def _extraer_json(respuesta: str) -> dict[str, str] | None:
    s = respuesta.strip()
    try:
        data = json.loads(s)
        if isinstance(data, dict):
            return {k: str(v) for k, v in data.items()}
    except Exception:
        pass

    m = re.search(r"```json\s*(\{.*?\})\s*```", s, flags=re.DOTALL | re.IGNORECASE)
    if m:
        try:
            data = json.loads(m.group(1))
            if isinstance(data, dict):
                return {k: str(v) for k, v in data.items()}
        except Exception:
            pass

    return None


def _extraer_bloques_legacy(respuesta: str) -> tuple[str, str, str, str]:
    episodio = respuesta.strip()
    maleta_u = ""
    diario_u = ""
    biblia_u = ""

    def split_marker(text: str, marker: str) -> tuple[str, str]:
        if marker not in text:
            return text, ""
        a, b = text.split(marker, 1)
        return a.strip(), b.strip()

    episodio, rest = split_marker(episodio, "MALETA_UPDATE")
    if rest:
        rest = rest.lstrip(":").strip()
        maleta_u, rest2 = split_marker(rest, "DIARIO_UPDATE")
        rest = rest2
    if rest:
        rest = rest.lstrip(":").strip()
        diario_u, rest2 = split_marker(rest, "BIBLIA_UPDATE")
        rest = rest2
    if rest:
        biblia_u = rest.lstrip(":").strip()

    return episodio, maleta_u, diario_u, biblia_u


def extraer_bloques(respuesta: str) -> tuple[str, str, str, str]:
    data = _extraer_json(respuesta)
    if data is not None:
        episodio = _limpiar_bloque(data.get("episodio", ""))
        maleta_u = _limpiar_bloque(data.get("maleta_update", ""))
        diario_u = _limpiar_bloque(data.get("diario_update", ""))
        biblia_u = _limpiar_bloque(data.get("biblia_update", ""))
        return episodio, maleta_u, diario_u, biblia_u

    episodio, maleta_u, diario_u, biblia_u = _extraer_bloques_legacy(respuesta)
    return (
        _limpiar_bloque(episodio),
        _limpiar_bloque(maleta_u),
        _limpiar_bloque(diario_u),
        _limpiar_bloque(biblia_u),
    )


def main() -> int:
    mundo = mundo_dir()
    logs_path = log_para_procesar(mundo)
    maleta_path = mundo / "maletas" / "maleta_001.md"
    biblia_path = mundo / "biblia" / "personajes.md"
    diario_path = mundo / "diario.md"

    logs = leer(logs_path)
    if not logs.strip():
        # No hay logs: no hacemos nada destructivo; dejamos una marca.
        stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        append(maleta_path, f"\n---\n\n(El narrador corrió sin logs: {stamp})\n")
        return 0

    maleta = leer(maleta_path)
    biblia = leer(biblia_path)
    diario = leer(diario_path)

    estado = parsear_estado_diario(diario)

    try:
        respuesta = completar(
            system=system_prompt_gonzalo(),
            user=user_prompt_cron(
                logs=logs, maleta=maleta, biblia=biblia, diario=diario, estado=estado,
            ),
            max_tokens=2000,
        )
        episodio, maleta_u, diario_u, biblia_u = extraer_bloques(respuesta)
    except Exception as e:
        # Fallback stub: deja evidencia y no toca biblia/diario.
        stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        episodio = (
            "Maleta 001 — Día 1 — (sin lugar)\n\n"
            f"(Narrador en modo stub: {stamp})\n\n"
            "Hoy solo tengo el registro crudo. Todavía no tengo voz.\n"
        )
        maleta_u = ""
        diario_u = ""
        biblia_u = ""
        append(maleta_path, f"\n---\n\nERROR LLM: {type(e).__name__}: {e}\n")

    # Episodio: por ahora lo anexamos al final de la maleta.
    append(maleta_path, "\n---\n\n" + episodio.strip() + "\n")

    if maleta_u.strip():
        append(maleta_path, "\n\n" + maleta_u.strip() + "\n")

    if diario_u.strip():
        escribir(diario_path, diario_u.strip() + "\n")

    if biblia_u.strip():
        escribir(biblia_path, biblia_u.strip() + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
