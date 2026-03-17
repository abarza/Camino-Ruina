from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

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


def log_de_hoy(mundo: Path) -> Path:
    today = dt.date.today().isoformat()
    return mundo / "logs" / f"{today}.md"


def system_prompt_gonzalo() -> str:
    # Versión compacta basada en docs/gonzalo_biblia_v3.md (system prompt).
    return (
        "Eres Gonzalo, un periodista gonzo que recorre el mundo documentando lo que encuentra.\n"
        "Escribes en español, en primera persona, con voz directa y seca.\n"
        "No escribes listas ni viñetas. No explicas lo que el lector puede sentir solo.\n"
        "No interpretas emociones ajenas: describes objetos, gestos y hechos.\n"
        "Formato del episodio: 'Maleta N — Día N — lugar'. 300 a 500 palabras. Cierre abierto.\n"
    )


def user_prompt_cron(*, logs: str, maleta: str, biblia: str, diario: str) -> str:
    return (
        "Eres Gonzalo. Tu tarea tiene dos partes:\n\n"
        "PARTE 1 — ESCRIBE EL EPISODIO\n"
        "Sigue tu voz y formato habitual.\n"
        "Encabezado: Maleta 001 — Día 1 — (lugar si aparece en logs)\n"
        "Elige el momento más cargado del día. No cubras todo.\n"
        "300 a 500 palabras. Cierre abierto.\n\n"
        "PARTE 2 — ACTUALIZA TUS ARCHIVOS\n"
        "MALETA_UPDATE (solo si hubo algo que valió guardar; puede estar vacío)\n"
        "DIARIO_UPDATE (máximo 3 líneas)\n"
        "BIBLIA_UPDATE (cambios en personajes)\n\n"
        f"---\nLOGS DEL DÍA:\n{logs}\n\n"
        f"---\nMALETA ACTIVA:\n{maleta}\n\n"
        f"---\nBIBLIA DE PERSONAJES:\n{biblia}\n\n"
        f"---\nDIARIO DE GONZALO:\n{diario}\n"
    )


def extraer_bloques(respuesta: str) -> tuple[str, str, str, str]:
    """
    Espera una respuesta con:
    - Episodio (texto libre)
    - MALETA_UPDATE:
    - DIARIO_UPDATE:
    - BIBLIA_UPDATE:
    """
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


def main() -> int:
    mundo = mundo_dir()
    logs_path = log_de_hoy(mundo)
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

    try:
        respuesta = completar(
            system=system_prompt_gonzalo(),
            user=user_prompt_cron(logs=logs, maleta=maleta, biblia=biblia, diario=diario),
            max_tokens=1100,
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

