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
        "REGLAS DE DECISIÓN (en orden de prioridad):\n"
        "1. Si hay mensajes o diálogos pendientes en pantalla → avanzar_mensajes.\n"
        "2. Si Gonzalo está Drowsy/Tired → dormir.\n"
        "3. Si Gonzalo está Hungry/Thirsty → comer_beber.\n"
        "4. Si hay un NPC cerca (d<=3) y no le ha hablado recientemente → hablar_npc.\n"
        "5. Si la posición (POS) no ha cambiado respecto al turno anterior → "
        "probar una dirección diferente o buscar escaleras (entrar_lugar, subir_nivel).\n"
        "6. Prefiere observar y explorar antes que pelear.\n"
        "7. Solo ataca si no tiene otra opción. Si puede huir, huye.\n"
        "8. Si no pasa nada interesante, se mueve a buscar algo nuevo.\n"
        "9. Varía las direcciones de movimiento — no repitas siempre la misma.\n\n"
        "Devuelves SOLO JSON válido: {\"intencion\":\"nombre\"}\n"
    )


def _user(estado: EstadoMinimo) -> str:
    opciones = [{"nombre": i.nombre, "descripcion": i.descripcion} for i in INTENCIONES_V0]
    return (
        "Elige una intención de la lista.\n\n"
        f"ESTADO_CONTEXTO: {estado.contexto}\n"
        "ESTADO DEL JUEGO:\n"
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
