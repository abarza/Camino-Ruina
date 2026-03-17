# Nota: Coordinación de Agentes — Camino a la Ruina

**Para:** Claude Code (o quien implemente)
**Contexto:** Se eligió Opción A (script Python simple). Esta nota es sobre lo que no debe perderse de vista.

---

## El riesgo real

El script del agente jugador es fácil. El riesgo es que terminen siendo 5 scripts sueltos sin estado compartido y el proyecto se vuelva frágil.

## Los agentes que van a existir (eventualmente)

1. **Jugador** — loop cada 5-10 min, lee pantalla, decide, manda teclas
2. **Narrador** — cron nocturno, escribe episodio, actualiza maleta/diario/biblia
3. **Legends** — consulta historia del mundo, enriquece contexto para el narrador
4. **Bot interactivo** — responde (o no) a mensajes de Twitch/Telegram
5. **Productor** — decide cuándo hay material para podcast o crónica escrita

No todos existen en Fase 1. Pero la estructura debe soportarlos desde el día uno.

## El filesystem como bus de coordinación

Nada de frameworks, nada de colas de mensajes. El directorio `mundo/` es la fuente de verdad.

```
mundo/
  logs/
    2026-03-16.md          ← el jugador escribe aquí cada turno
  maletas/
    maleta_001.md          ← el narrador actualiza si hubo algo que valió
  biblia/
    personajes.md          ← el narrador actualiza cada noche
    fortaleza_actual.md
  diario.md                ← estado interno de Gonzalo
  legends/
    mundo.md               ← export de Legends, consultable
```

Cada agente sabe qué archivos lee y qué archivos escribe. No hay colisiones si se respeta eso.

## Reglas de convivencia

- **Un solo writer por archivo.** Si dos agentes necesitan escribir al mismo, uno append y el otro reescribe, nunca los dos reescriben.
- **Logs son append-only.** El jugador solo agrega al final del log del día. Nunca edita líneas anteriores.
- **El narrador es el único que toca maletas, diario y biblia.** El jugador no sabe que existen.
- **Timestamps en todo.** Cada entrada de log lleva hora. El narrador necesita saber el orden.
- **El jugador no interpreta.** Escribe lo que pasó en crudo: qué vio en pantalla, qué decidió, qué teclas mandó. La interpretación narrativa es trabajo del narrador.

## Lo que el Agente Jugador debe loguear por turno

```
## Turno 14:35

**Pantalla:** [texto capturado de tmux]
**Contexto:** Estamos en la entrada de Ïteb Zulban, hay un NPC al norte
**Decisión:** Hablar con el NPC
**Teclas:** [secuencia enviada]
**Resultado:** [texto capturado después de enviar]
```

Ese formato crudo es lo que el narrador convierte en prosa de Gonzalo.

## Lo que NO hay que hacer todavía

- No implementar el bot interactivo
- No implementar el productor de podcasts
- No conectar Telegram ni Twitch
- No optimizar — que funcione primero

## Lo que SÍ hay que dejar listo desde el día uno

- La estructura de `mundo/` creada y respetada
- El log del jugador con formato parseble
- El cron nocturno leyendo de `mundo/` y escribiendo a `mundo/`
- Todo versionado en git para que las maletas tengan historia

---

*Si la estructura está bien desde el principio, agregar agentes después es copiar un script y decirle qué lee y qué escribe. Si no está, es reescribir todo.*
