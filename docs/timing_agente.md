# Timing del Agente Jugador

## Principio

El loop NO es un timer fijo. El agente es reactivo con delays variables según contexto. El LLM decide intenciones, no acciones individuales.

## Dos niveles de decisión

### Nivel 1 — LLM (decisiones estratégicas)
El LLM recibe la pantalla capturada y el contexto detectado, y elige una **intención** del vocabulario disponible (16 intenciones en `scripts/intenciones.py`):
- Movimiento: `explorar_norte`, `explorar_sur`, `explorar_este`, `explorar_oeste`
- Interacción: `hablar_npc`, `mirar_alrededor`, `recoger_objeto`
- Navegación: `entrar_lugar`, `subir_nivel`, `viajar`
- Supervivencia: `comer`, `descansar`, `inventario`
- Combate: `atacar`, `huir`
- Pasivo: `esperar`

Prioridades del decisor: hablar con NPCs > observar > explorar > huir > atacar.
Se consulta solo cuando hay una decisión real que tomar. No cada tick.

### Nivel 2 — Script (ejecución mecánica)
El script traduce la intención en secuencias de teclas predefinidas y las ejecuta sin volver a consultar al LLM:
- `explorar_norte` = 3 pasos al norte (KP_8 × 3)
- `comer` = una tecla (`e`) que abre el menú
- `descansar` = una tecla (`Z`) para acampar

## Delays por contexto

| Contexto | Delay entre acciones | Razón |
|---|---|---|
| Viaje / exploración | 2-3 segundos | Se ve fluido, Gonzalo caminando |
| Combate | 0.5-1 segundo | Tiene que reaccionar rápido |
| Conversación NPC | 5-10 segundos | Parece que piensa qué preguntar |
| Menús / inventario | 0.3-0.5 segundos | Nadie quiere ver navegación lenta |
| Idle / observando | 10-15 segundos | Gonzalo mirando, tomando notas |

## Cuándo consultar al LLM

- Al llegar a un lugar nuevo (ciudad, ruina, cueva)
- Al encontrar un NPC
- Al iniciar o terminar un combate
- Cuando cambia el contexto significativamente (herido, hambre, noche)
- Cuando termina de ejecutar la intención anterior

## Cuándo NO consultar al LLM

- En medio de una caminata (el script ejecuta solo)
- Navegando menús (secuencias fijas)
- Acciones mecánicas (comer, dormir, equipar)
- Cada tile de movimiento individual

## Impacto

Esto baja las llamadas al LLM de ~300/hora (si consultas cada acción) a ~20-30/hora (solo decisiones reales). El stream se ve fluido y los costos de API no explotan.
