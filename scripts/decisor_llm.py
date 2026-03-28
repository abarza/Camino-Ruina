from __future__ import annotations

import json
from dataclasses import dataclass

from scripts.intenciones import INTENCIONES_V0, Intencion, intencion_por_nombre
from scripts.llm import completar


@dataclass(frozen=True)
class EstadoMinimo:
    pantalla: str
    contexto: str
    ticks_atascado: int = 0


def _system() -> str:
    return (
        "Eres el decisor de Gonzalo, un periodista que explora el mundo de "
        "Dwarf Fortress en Adventure Mode.\n\n"
        "REGLAS OBLIGATORIAS (en orden de prioridad):\n"
        "1. Si SLEEP > 40000 → dormir. No hay excepción.\n"
        "2. Si HUNGER > 50000 o THIRST > 40000 → comer_beber. No hay excepción.\n"
        "3. Si el contexto es 'conversación' y hay CONV_CHOICES → "
        "elegir hablar con alguien interesante (hablar_npc) o avanzar_mensajes para salir.\n"
        "4. Si TICKS_ATASCADO >= 3 → la dirección actual no funciona. "
        "Probar: otra dirección, entrar_lugar, subir_nivel, o viajar.\n"
        "5. Si hay un NPC cerca (d<=3) y no estás en necesidad → hablar_npc.\n"
        "6. Prefiere observar (mirar_alrededor, buscar_area) antes que pelear.\n"
        "7. Solo ataca si no tiene otra opción. Si puede huir, huye.\n"
        "8. Varía las direcciones: no repitas siempre el mismo explorar_X.\n"
        "9. Si no pasa nada interesante, muévete a buscar algo nuevo.\n\n"
        "Devuelves SOLO JSON válido: {\"intencion\":\"nombre\"}\n"
    )


def _user(estado: EstadoMinimo) -> str:
    opciones = [{"nombre": i.nombre, "descripcion": i.descripcion} for i in INTENCIONES_V0]
    atascado_msg = ""
    if estado.ticks_atascado >= 3:
        atascado_msg = (
            f"\n⚠️ ATASCADO: la posición no ha cambiado en {estado.ticks_atascado} turnos. "
            "Cambia de dirección o busca escaleras/salidas.\n"
        )
    return (
        f"CONTEXTO: {estado.contexto}\n"
        f"{atascado_msg}"
        "ESTADO DEL JUEGO:\n"
        f"{estado.pantalla}\n\n"
        "INTENCIONES:\n"
        f"{json.dumps(opciones, ensure_ascii=False)}\n\n"
        '→ {\"intencion\":\"nombre\"}\n'
    )


def decidir_intencion(estado: EstadoMinimo) -> Intencion:
    out = completar(system=_system(), user=_user(estado), max_tokens=120)
    data = json.loads(out)
    nombre = str(data.get("intencion", "esperar"))
    picked = intencion_por_nombre(nombre)
    return picked or intencion_por_nombre("esperar") or INTENCIONES_V0[-1]
