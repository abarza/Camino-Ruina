from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Intencion:
    nombre: str
    descripcion: str
    # Secuencia mecánica (teclas tmux) para ejecutar sin más consultas.
    teclas: list[str]
    contexto_sugerido: str


INTENCIONES_V0: list[Intencion] = [
    Intencion(
        nombre="explorar_basico",
        descripcion="Moverse y observar, sin objetivo específico.",
        teclas=["KP_8", "KP_8", "KP_6", "KP_6", "."],
        contexto_sugerido="exploración",
    ),
    Intencion(
        nombre="esperar",
        descripcion="Quedarse quieto y observar un rato.",
        teclas=["."],
        contexto_sugerido="idle",
    ),
]


def intencion_por_nombre(nombre: str) -> Intencion | None:
    for i in INTENCIONES_V0:
        if i.nombre == nombre:
            return i
    return None

