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
    # --- Movimiento ---
    Intencion(
        nombre="explorar_norte",
        descripcion="Caminar varios pasos al norte.",
        teclas=["KP_8", "KP_8", "KP_8"],
        contexto_sugerido="exploración",
    ),
    Intencion(
        nombre="explorar_sur",
        descripcion="Caminar varios pasos al sur.",
        teclas=["KP_2", "KP_2", "KP_2"],
        contexto_sugerido="exploración",
    ),
    Intencion(
        nombre="explorar_este",
        descripcion="Caminar varios pasos al este.",
        teclas=["KP_6", "KP_6", "KP_6"],
        contexto_sugerido="exploración",
    ),
    Intencion(
        nombre="explorar_oeste",
        descripcion="Caminar varios pasos al oeste.",
        teclas=["KP_4", "KP_4", "KP_4"],
        contexto_sugerido="exploración",
    ),
    # --- Interacción (genera contenido narrativo) ---
    Intencion(
        nombre="hablar_npc",
        descripcion="Iniciar conversación con un NPC cercano.",
        teclas=["k"],
        contexto_sugerido="conversación",
    ),
    Intencion(
        nombre="mirar_alrededor",
        descripcion="Observar el entorno, examinar objetos o señales cercanas.",
        teclas=["l"],
        contexto_sugerido="exploración",
    ),
    Intencion(
        nombre="recoger_objeto",
        descripcion="Recoger un objeto del suelo.",
        teclas=["g"],
        contexto_sugerido="exploración",
    ),
    # --- Navegación ---
    Intencion(
        nombre="entrar_lugar",
        descripcion="Bajar escaleras o entrar a un nivel inferior.",
        teclas=[">"],
        contexto_sugerido="exploración",
    ),
    Intencion(
        nombre="subir_nivel",
        descripcion="Subir escaleras o salir de un nivel inferior.",
        teclas=["<"],
        contexto_sugerido="exploración",
    ),
    Intencion(
        nombre="viajar",
        descripcion="Viaje rápido para moverse a otra zona del mapa.",
        teclas=["T"],
        contexto_sugerido="exploración",
    ),
    # --- Supervivencia ---
    Intencion(
        nombre="comer",
        descripcion="Comer algo del inventario para recuperar energía.",
        teclas=["e"],
        contexto_sugerido="inventario",
    ),
    Intencion(
        nombre="descansar",
        descripcion="Dormir o acampar.",
        teclas=["Z"],
        contexto_sugerido="idle",
    ),
    Intencion(
        nombre="inventario",
        descripcion="Revisar qué llevas encima.",
        teclas=["i"],
        contexto_sugerido="inventario",
    ),
    # --- Combate ---
    Intencion(
        nombre="atacar",
        descripcion="Atacar a un enemigo cercano.",
        teclas=["A"],
        contexto_sugerido="combate",
    ),
    Intencion(
        nombre="huir",
        descripcion="Escapar corriendo del peligro (sprint al sur).",
        teclas=["KP_2", "KP_2", "KP_2", "KP_2", "KP_2"],
        contexto_sugerido="combate",
    ),
    # --- Pasivo ---
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

