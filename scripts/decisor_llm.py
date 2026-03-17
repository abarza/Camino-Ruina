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
        "Eres un decisor para un agente jugador. No escribes prosa.\n"
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

