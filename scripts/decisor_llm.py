from __future__ import annotations

import json
from dataclasses import dataclass

from scripts.intenciones import INTENCIONES_V0, Intencion, intencion_por_nombre
from scripts.llm import completar


@dataclass(frozen=True)
class EstadoMinimo:
    pantalla: str
    contexto: str


def _system() -> str:
    return (
        "Eres el decisor de Gonzalo, un periodista que explora el mundo de "
        "Dwarf Fortress en Adventure Mode.\n\n"
        "PRIORIDADES DE GONZALO (en orden):\n"
        "1. Si hay un NPC cerca, casi siempre quiere hablar (hablar_npc).\n"
        "2. Prefiere observar y explorar antes que pelear.\n"
        "3. Solo ataca si no tiene otra opción. Si puede huir, huye.\n"
        "4. Come y descansa cuando lo necesita.\n"
        "5. Si no pasa nada interesante, se mueve a buscar algo nuevo.\n\n"
        "Devuelves SOLO JSON válido. Nada más.\n"
    )


def _user(estado: EstadoMinimo) -> str:
    opciones = [{"nombre": i.nombre, "descripcion": i.descripcion} for i in INTENCIONES_V0]
    return (
        "Elige una intención de la lista, o 'esperar' si no estás seguro.\n\n"
        f"ESTADO_CONTEXTO: {estado.contexto}\n"
        "PANTALLA:\n"
        f"{estado.pantalla}\n\n"
        "INTENCIONES_DISPONIBLES:\n"
        f"{json.dumps(opciones, ensure_ascii=False)}\n\n"
        "Formato de salida:\n"
        '{"intencion":"nombre"}\n'
    )


def decidir_intencion(estado: EstadoMinimo) -> Intencion:
    out = completar(system=_system(), user=_user(estado), max_tokens=120)
    data = json.loads(out)
    nombre = str(data.get("intencion", "esperar"))
    picked = intencion_por_nombre(nombre)
    return picked or intencion_por_nombre("esperar") or INTENCIONES_V0[-1]

