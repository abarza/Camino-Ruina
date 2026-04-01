# Plan de Mejoras del Agente — Fase 6

Fecha: 2026-04-01
Estado: En progreso

El agente funciona mecánicamente pero interactúa poco con el mundo. Gonzalo camina, come cuando tiene hambre, y duerme cuando está cansado. Pero no habla con NPCs de forma efectiva, no recoge objetos, no sabe qué lleva encima, y no busca civilización cuando está perdido. Este plan aborda esas carencias.

---

## 1. Extender DFHack Lua — Darle ojos al agente

El agente solo "ve" lo que `dfhack_state.lua` reporta. Hoy eso es: posición, HP, hambre/sed/sueño, NPCs cercanos, y el menú actual. Falta información crítica.

**Archivo:** `scripts/dfhack_state.lua`

### 1.1 Inventario del aventurero (Prioridad: ALTA)

Agregar bloque `INVENTORY:` con los items que lleva Gonzalo.

```
INVENTORY: copper whip (weapon); porcupine leather waterskin (empty); turkey leather dress (armor); 3x biscuit (food)
```

Esto permite:
- Saber si tiene comida antes de intentar comer (evita loop de "lick waterskin")
- Saber si el waterskin está vacío → buscar agua
- Saber qué arma/armadura lleva
- Decidir si recoger algo del suelo es útil

**Implementación:** Iterar `adv.inventory` en Lua, extraer nombre y tipo de cada item.

### 1.2 Items en el suelo (Prioridad: MEDIA)

Agregar bloque `GROUND:` con items en la posición actual.

```
GROUND: iron short sword; leather bag (3 items)
```

Esto permite:
- Decidir si vale la pena recoger algo
- Detectar comida/agua en el suelo

**Implementación:** Iterar items en la posición del aventurero via `df.global.world.items.all` filtrando por `pos == adv.pos` y `flags.on_ground`.

### 1.3 Detección de hostilidad (Prioridad: MEDIA)

Agregar flag de hostilidad al NEARBY:

```
NEARBY: Staddat Lesnoamec (HUMAN, d=3, friendly); (sin nombre) (CRUNDLE, d=5, hostile)
```

**Implementación:** Comparar `u.civ_id` con `adv.civ_id`, o usar `dfhack.units.isEnemy(adv, u)` si está disponible en 0.47.

### 1.4 Edificios cercanos (Prioridad: BAJA)

Agregar bloque `BUILDINGS:` cuando hay estructuras cerca (well, shop, door).

```
BUILDINGS: well (d=3); door (d=1)
```

**Implementación:** Iterar `df.global.world.buildings.all` filtrando por distancia al aventurero.

---

## 2. Mejorar intenciones del agente

**Archivo:** `scripts/intenciones.py`

### 2.1 Acercarse a NPC (NUEVA — Prioridad: ALTA)

Hoy el agente intenta `hablar_npc` (tecla `k`) pero si nadie está a d<=2, el menú no muestra NPCs reales. Necesita una intención para caminar HACIA el NPC más cercano.

```python
Intencion(
    nombre="acercarse_npc",
    descripcion="Caminar hacia el NPC más cercano para poder hablar.",
    teclas=[],  # calculadas dinámicamente según posición relativa del NPC
    contexto_sugerido="exploración",
)
```

**Implementación en agente_jugador.py:** Cuando el LLM elige `acercarse_npc`, leer NEARBY, extraer posición relativa del NPC más cercano, y calcular las teclas de dirección para acercarse (KP_8 si está al norte, KP_6 si está al este, etc.).

### 2.2 Interactuar con edificio (NUEVA — Prioridad: MEDIA)

Para usar pozos, puertas, y otros objetos interactivos.

```python
Intencion(
    nombre="interactuar",
    descripcion="Interactuar con un objeto o edificio cercano (pozo, puerta, etc.).",
    teclas=["I"],  # o la tecla correcta según DF 0.47
    contexto_sugerido="exploración",
)
```

### 2.3 Mejorar huir (Prioridad: BAJA)

Hoy huir es "sprint al sur". Debería huir en la dirección opuesta al hostil más cercano.

**Implementación:** Calcular dirección opuesta al NEARBY hostil más cercano y generar las teclas correspondientes.

---

## 3. Mejorar lógica del agente

**Archivo:** `scripts/agente_jugador.py`

### 3.1 Conversación efectiva (Prioridad: ALTA)

Problemas actuales:
- El menú "Who will you talk to?" a veces solo tiene la deity → ya corregido (quitamos filtro)
- Cuando hay NPCs en NEARBY pero a d>3, el agente intenta hablar y falla
- No se acerca al NPC antes de intentar hablar

**Fix:**
- Antes de elegir `hablar_npc`, verificar que hay alguien en NEARBY con d<=3
- Si no, bloquear `hablar_npc` y sugerir `acercarse_npc`
- Después de seleccionar un NPC, manejar el menú `ConversationSpeak` con más inteligencia (ya existe `_elegir_tema_conversacion` pero puede mejorar)

### 3.2 Manejo de menús de pickup (Prioridad: MEDIA)

Cuando el agente presiona `g` (recoger), se abre un menú con los items disponibles. Hoy el agente no sabe manejar ese menú — se queda en FOCUS de menú y cierra con LEAVESCREEN.

**Fix:**
- Detectar FOCUS `dungeonmode/GetItems` o similar
- Si hay items, seleccionar el primero con SELECT
- O mejor: con inventario visible, solo recoger si hay algo útil

### 3.3 Búsqueda de agua inteligente (Prioridad: MEDIA)

El personaje está constantemente deshidratado. El agente debería:
1. Detectar que el waterskin está vacío (via inventario)
2. Buscar un Well cercano (via buildings)
3. Acercarse y interactuar

Esto depende de 1.1 (inventario) y 1.4 (buildings). Es una mejora de segunda etapa.

### 3.4 Detección de combate y escape (Prioridad: MEDIA)

Hoy el agente no distingue hostiles de amigables en NEARBY. Con la detección de hostilidad (1.3):
- Si hay un hostil a d<5 → priorizar escape automáticamente (sin consultar LLM)
- Dirección de escape: opuesta al hostil

### 3.5 Movimiento anti-atascamiento (Prioridad: BAJA)

El agente ya detecta `ticks_atascado` pero solo cambia dirección. Podría:
- Probar escaleras arriba/abajo
- Usar fast travel si lleva mucho tiempo sin encontrar nada interesante
- Buscar puertas/entradas

---

## 4. Mejorar el decisor LLM

**Archivo:** `scripts/decisor_llm.py`

### 4.1 Incluir inventario en el prompt (Prioridad: ALTA)

Con la extensión de Lua (1.1), el estado del juego incluirá INVENTORY. El LLM podrá tomar mejores decisiones:
- "Tiene comida → no buscar comida"
- "Waterskin vacío → buscar agua"
- "Tiene arma → puede pelear si es necesario"

### 4.2 Contexto de "qué acaba de pasar" (Prioridad: MEDIA)

Hoy el LLM solo ve el estado actual. No sabe qué pasó en los últimos 5 turnos. Agregar un mini-historial:

```
ÚLTIMOS 3 TURNOS: hablar_npc (cerró sin NPC), explorar_norte, mirar_alrededor
```

Esto evita que repita la misma acción fallida.

### 4.3 Reglas de prioridad mejoradas (Prioridad: BAJA)

El system prompt actual tiene 9 reglas. Agregar:
- "Si NEARBY tiene un NPC con nombre a d>3, acercarse antes de hablar"
- "Si INVENTORY no tiene comida y estás hambriento, buscar asentamientos"
- "Si llevas más de 50 turnos sin ver un NPC con nombre, considerar viajar"

---

## 5. Orden de implementación

### Etapa A — Visibilidad (hacer que el agente "vea" más)
1. [x] Inventario en Lua (1.1)
2. [x] Hostilidad en NEARBY (1.3)
3. [x] Items en el suelo en Lua (1.2) — adelantado de Etapa C
4. [x] Incluir inventario en prompt del decisor (4.1)
5. [x] Mini-historial de turnos en el prompt (4.2) — adelantado de Etapa B
6. [x] Reglas de hostilidad y pickup en decisor (4.3)

### Etapa B — Interacción (hacer que el agente "haga" más)
4. [x] Acercarse a NPC si d>3 en vez de hablar (2.1 + 3.1)
5. [x] Bloquear `hablar_npc` si nadie con nombre a d<=3 (3.1)
6. [x] Mini-historial de turnos en el prompt (4.2)
7. [x] Manejo de menú de pickup GetItems (3.2)

### Etapa C — Supervivencia (hacer que no muera)
8. [x] Detección de combate y escape automático (3.4)
9. [x] Items en el suelo en Lua (1.2) — adelantado a Etapa A
10. [ ] Búsqueda de agua inteligente (3.3)

### Etapa D — Exploración (hacer que encuentre cosas)
11. [ ] Edificios cercanos en Lua (1.4)
12. [ ] Interacción con edificios (2.2)
13. [ ] Huir inteligente (2.3)
14. [ ] Movimiento anti-atascamiento mejorado (3.5)

---

## Archivos clave

| Archivo | Qué se modifica |
|---------|----------------|
| `scripts/dfhack_state.lua` | Agregar INVENTORY, GROUND, hostilidad, BUILDINGS |
| `scripts/intenciones.py` | Nuevas intenciones: acercarse_npc, interactuar |
| `scripts/agente_jugador.py` | Lógica de conversación, pickup, escape, acercarse |
| `scripts/decisor_llm.py` | Inventario en prompt, mini-historial, reglas mejoradas |
| `scripts/dfhack_io.py` | Sin cambios esperados |

## Dependencias

```
1.1 (inventario Lua) ──→ 4.1 (inventario en prompt) ──→ 3.3 (búsqueda de agua)
1.3 (hostilidad Lua) ──→ 3.4 (escape automático)
1.4 (buildings Lua)  ──→ 2.2 (interactuar) ──→ 3.3 (búsqueda de agua)
2.1 (acercarse_npc)  ──→ 3.1 (conversación efectiva)
```
