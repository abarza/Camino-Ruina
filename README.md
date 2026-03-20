## Camino a la Ruina (OpenClaw)

Proyecto para correr un "corresponsal" (Gonzalo) 24/7 en **Dwarf Fortress — Adventure Mode**, con:

- **Agente Jugador**: juega, decide y loguea en crudo.
- **Narrador nocturno**: convierte logs en crónica diaria y actualiza maletas/diario/biblia.
- **Filesystem como bus**: `mundo/` es la fuente de verdad compartida entre agentes.

### Documentación

- Biblia/tono/prompts: [`docs/gonzalo_biblia_v3.md`](docs/gonzalo_biblia_v3.md)
- Arquitectura (Docker/volúmenes): [`docs/arquitectura.md`](docs/arquitectura.md)
- Coordinación (contratos de archivos): [`docs/nota_coordinacion_agentes.md`](docs/nota_coordinacion_agentes.md)
- Timing del jugador: [`docs/timing_agente.md`](docs/timing_agente.md)
- Roadmap por fases: [`docs/plan_fases.md`](docs/plan_fases.md)

### Estructura (fuente de verdad)

El directorio `mundo/` persiste por volumen y contiene logs y estado narrativo.

### Operación (mínimo)

- **Config**: copia `.env.example` a `.env` y completa el proveedor LLM si vas a usar narrador/decisor.
- **Levantar contenedor**:

```bash
docker compose up --build -d
```

- **Setup inicial (una sola vez)**: attachar a la sesión tmux para crear mundo y aventurero.

```bash
docker compose exec camino tmux attach -t df
# Navegar menús de DF: Create New World → Start Playing → Adventurer → crear personaje
# Para salir de tmux sin cerrarlo: Ctrl+B luego D
```

- **Agente jugador v0 (loop mecánico)**:

```bash
docker compose exec camino python3 -m scripts.agente_jugador
```

- **Agente jugador con LLM (16 intenciones)**:

```bash
docker compose exec camino env USE_LLM_INTENTIONS=1 python3 -m scripts.agente_jugador
```

- **Narrador nocturno (manual)**:

```bash
docker compose exec camino python3 -m scripts.narrador_nocturno
```

- **Ver pantalla de DF**:

```bash
docker compose exec camino tmux capture-pane -t df:0 -p
```

- **Consultar estado via DFHack**:

```bash
docker compose exec camino /opt/df/dfhack-run lua "dofile('/gonzalo/scripts/dfhack_state.lua')"
```

### Stack técnico

- **DF 0.47.05** (text mode, ncurses) + **DFHack 0.47.05-r8** en tmux
- `PRINT_MODE:TEXT` — DF corre como aplicación de terminal pura
- El agente lee estado via `dfhack-run` (Lua) y envía teclas via `tmux send-keys`
- Lectura de pantalla via `tmux capture-pane` (texto directo, sin OCR)
- Sin dependencias gráficas (no Xvfb, SDL2, x11vnc, xdotool)

### Inbox (futuro bot)

Mensajes externos (cuando existan) entrarán por `mundo/inbox/`. Ver `mundo/inbox/README.md`.
