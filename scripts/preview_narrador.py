"""Preview del narrador: genera la crónica sin tocar estado real.

Uso:
    python3 -m scripts.preview_narrador              # usa logs de hoy (o el más reciente)
    python3 -m scripts.preview_narrador 2026-03-20   # usa logs de fecha específica

El resultado se escribe en mundo/preview/ y se muestra en stdout.
No toca maleta, diario, biblia ni markers de estado.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

from scripts.narrador_nocturno import (
    escribir,
    estimar_tokens,
    extraer_bloques,
    leer,
    load_config,
    context_window,
    log_de_hoy,
    log_mas_reciente,
    mundo_dir,
    resumir_maleta,
    parsear_estado_diario,
    system_prompt_gonzalo,
    truncar_logs,
    user_prompt_cron,
)
from scripts.llm import completar


def main() -> int:
    mundo = mundo_dir()
    preview_dir = mundo / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)

    # Determinar qué log usar.
    if len(sys.argv) > 1:
        fecha = sys.argv[1].strip()
        logs_path = mundo / "logs" / f"{fecha}.md"
    else:
        logs_path = log_de_hoy(mundo)
        if not logs_path.exists():
            logs_path = log_mas_reciente(mundo)
        if logs_path is None:
            print("No hay logs disponibles.", file=sys.stderr)
            return 1

    if not logs_path.exists():
        print(f"Log no encontrado: {logs_path}", file=sys.stderr)
        return 1

    print(f"[preview] Log: {logs_path.name}")

    logs = leer(logs_path)
    maleta = leer(mundo / "maletas" / "maleta_001.md")
    biblia = leer(mundo / "biblia" / "personajes.md")
    diario = leer(mundo / "diario.md")
    estado = parsear_estado_diario(diario)

    # Truncar logs igual que el narrador real.
    cfg = load_config()
    max_ctx = context_window(cfg.model)
    overhead_fijo = 5350
    maleta_resumida = resumir_maleta(maleta)
    overhead_contexto = estimar_tokens(maleta_resumida) + estimar_tokens(biblia) + estimar_tokens(diario)
    log_budget = max_ctx - overhead_fijo - overhead_contexto

    def _intentar_con_budget(budget: int) -> str:
        logs_t = truncar_logs(logs, budget)
        return completar(
            system=system_prompt_gonzalo(),
            user=user_prompt_cron(
                logs=logs_t, maleta=maleta, biblia=biblia, diario=diario, estado=estado,
            ),
            max_tokens=2000,
        )

    print("[preview] Llamando al LLM...")
    try:
        respuesta = _intentar_con_budget(log_budget)
        episodio, maleta_u, diario_u, biblia_u = extraer_bloques(respuesta)
    except Exception as e:
        if "context_length_exceeded" in str(e) or "context length" in str(e).lower():
            reduced = int(log_budget * 0.6)
            print(f"[preview] Contexto excedido, reintentando con budget reducido ({reduced} tokens)...")
            try:
                respuesta = _intentar_con_budget(reduced)
                episodio, maleta_u, diario_u, biblia_u = extraer_bloques(respuesta)
            except Exception as e2:
                print(f"[preview] Error LLM en retry: {e2}", file=sys.stderr)
                return 1
        else:
            print(f"[preview] Error LLM: {e}", file=sys.stderr)
            return 1

    # Escribir preview a archivo (sin tocar nada real).
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_path = preview_dir / f"preview_{stamp}.md"

    contenido = f"# Preview — {logs_path.name}\n\n"
    contenido += "## Episodio\n\n"
    contenido += episodio.strip() + "\n"

    if maleta_u.strip():
        contenido += "\n---\n\n## Maleta Update\n\n"
        contenido += maleta_u.strip() + "\n"

    if diario_u.strip():
        contenido += "\n---\n\n## Diario Update\n\n"
        contenido += diario_u.strip() + "\n"

    if biblia_u.strip():
        contenido += "\n---\n\n## Biblia Update\n\n"
        contenido += biblia_u.strip() + "\n"

    escribir(out_path, contenido)

    # Mostrar en stdout.
    print()
    print("=" * 60)
    print(contenido)
    print("=" * 60)
    print(f"\n[preview] Guardado en: {out_path}")
    print("[preview] Estado real NO fue modificado.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
