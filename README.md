## Camino a la Ruina (OpenClaw)

Proyecto para correr un “corresponsal” (Gonzalo) 24/7 en **Dwarf Fortress — Adventure Mode**, con:

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
docker compose up --build
```

- **Sesión tmux del juego**: por defecto `TMUX_SESSION=df` dentro del contenedor.
  - Si montas DF/DFHack en `/opt/df`, el entrypoint ejecuta `DF_CMD` (default `./dwarfort`).
  - Puedes cambiarlo con `.env`/variables (`DF_CMD=./dfhack`, por ejemplo).
  - En modo `./dfhack`, el contenedor usa un launcher compatible (preload de `libdfhack.so`, sin `setarch`).
- **Captura manual (logs crudos)**:

```bash
python3 -m scripts.captura_pantalla
```

- **Agente jugador v0 (loop mecánico)**:

```bash
python3 -m scripts.agente_jugador
```

- **Agente jugador con LLM (16 intenciones)**:

```bash
USE_LLM_INTENTIONS=1 python3 -m scripts.agente_jugador
```

- **Narrador nocturno (manual)**:

```bash
python3 -m scripts.narrador_nocturno
```

### Inbox (futuro bot)

Mensajes externos (cuando existan) entrarán por `mundo/inbox/`. Ver `mundo/inbox/README.md`.
