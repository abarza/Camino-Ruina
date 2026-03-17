# Plan por fases — Camino a la Ruina

Este documento traduce la visión de `docs/` en un **roadmap ejecutable**, con **criterios de salida** por fase.

Fuentes: [`docs/gonzalo_biblia_v3.md`](gonzalo_biblia_v3.md), [`docs/arquitectura.md`](arquitectura.md), [`docs/nota_coordinacion_agentes.md`](nota_coordinacion_agentes.md), [`docs/timing_agente.md`](timing_agente.md), [`docs/ideas.md`](ideas.md).

## Estado actual (auditoría con evidencia)

Fecha de auditoría: 2026-03-17.

### Inventario (evidencia)

- `docker-compose.yml`
- `docker/`:
  - `docker/Dockerfile`
  - `docker/entrypoint.sh`
  - `docker/launch_df.sh`
  - `docker/cron_narrador`
  - `docker/README.md`
- `scripts/`:
  - `scripts/captura_pantalla.py`
  - `scripts/agente_jugador.py`
  - `scripts/narrador_nocturno.py`
  - `scripts/tmux_io.py`
  - `scripts/llm.py`
  - `scripts/intenciones.py`
  - `scripts/decisor_llm.py`
- `mundo/` (bus persistente):
  - `mundo/diario.md`
  - `mundo/logs/2026-03-17.md` (hay snapshots de ejecución)
  - `mundo/maletas/maleta_001.md`
  - `mundo/biblia/personajes.md`, `mundo/biblia/fortaleza_actual.md`
  - `mundo/legends/mundo.md`
  - `mundo/inbox/README.md` (gancho futuro)
- Config:
  - `.env.example`
  - `requirements.txt`

### Validación de criterios por fase (cumplido/pendiente)

> Nota operativa actualizada: en este entorno **sí** hay Docker/Compose y se pudo ejecutar `docker compose config` y `docker compose run` para validar montaje de volúmenes y arranque base del contenedor.

#### Fase 0 — Arranque del repo y estructura

- **Criterios**
  - ✅ `mundo/` existe con placeholders.
  - ✅ `.env.example` existe.
  - ✅ `docs/plan_fases.md` existe.
- **Evidencia**
  - `mundo/diario.md`, `mundo/maletas/maleta_001.md`, `mundo/biblia/*`, `mundo/legends/mundo.md`
  - `.env.example`

#### Fase 1 — Infraestructura Docker + DF + canal de logs

- **Criterios**
  - ✅ `docker compose up --build -d` levanta el contenedor de servicio.
  - ✅ Volúmenes quedan montados (`./mundo -> /gonzalo/mundo`, `./saves -> /df/data/save`, `./df -> /opt/df`).
  - ✅ DF corre en tmux bajo Xvfb (`pgrep` muestra `Xvfb :99` y `./dwarfort` activos).
  - ✅ Se puede generar `mundo/logs/YYYY-MM-DD.md` con timestamps (vía script).
  - ✅ Volúmenes definidos y observables dentro de contenedor.
- **Evidencia**
  - `docker-compose.yml` monta `./mundo:/gonzalo/mundo` y `./saves:/df/data/save`.
  - `docker-compose.yml` monta `./df:/opt/df` (DF Classic + DFHack).
  - `docker/Dockerfile` instala `xvfb`, `tmux`, `cron`, `python3` y configura cron.
  - `docker/entrypoint.sh` arranca Xvfb, crea sesión tmux (`TMUX_SESSION=df`) y ahora ejecuta `DF_CMD` configurable (default `./dwarfort`).
  - `scripts/tmux_io.py` sanitiza captura de pane y filtra ruido de arranque (`Broken unicode`, `Unknown SDLKey`, etc.).
  - Captura de pane a logs: `scripts/captura_pantalla.py`.
  - `mundo/logs/2026-03-17.md` contiene snapshots y turnos reales del agente (`## Snapshot 23:03:15`, `## Turno 23:03`) y snapshots limpios tras filtrado (`## Snapshot 23:21:04`).

**Compatibilidad DFHack en contenedor (resuelto en esta auditoría):**
- Se agregó launcher `docker/launch_df.sh`: cuando `DF_CMD=./dfhack`, lanza `./dwarfort` con `LD_PRELOAD=./hack/libdfhack.so` (sin `setarch`).
- Validación: `docker compose run --rm -e DF_CMD=./dfhack ...` levanta tmux + proceso `./dwarfort` sin error `setarch ... Operation not permitted`.
- `DF_CMD=./dwarfort` se mantiene como default estable.

**Calidad de captura (mitigada en Fase 1):**
- Se filtró ruido de consola en la capa de captura (`scripts/tmux_io.py`), mejorando legibilidad y señal para jugador/narrador.

#### Fase 2 — Agente Jugador v0 (script + logging estructurado)

- **Criterios**
  - ✅ Existe loop del agente (proceso largo).
  - ✅ El log diario es estructurado y parseable con timestamps de turno.
  - ✅ Delays por contexto básicos implementados.
- **Evidencia**
  - `scripts/agente_jugador.py` escribe bloques `## Turno HH:MM` con `Pantalla/Contexto/Decisión/Teclas/Resultado`.
  - `scripts/tmux_io.py` implementa `capture_pane()` y `send_raw_keys()` (IO con tmux).

#### Fase 3 — Narrador nocturno v0 (cron + crónica diaria mínima)

- **Criterios**
  - ✅ Ejecutable manualmente (script existe y opera sobre `mundo/`).
  - ⏳ Cron corre 1 vez por noche sin errores en operación continua (pendiente de corrida nocturna completa).
- **Evidencia**
  - `scripts/narrador_nocturno.py`:
    - Lee `mundo/logs/YYYY-MM-DD.md` y actualiza `mundo/maletas/maleta_001.md`.
    - Si no hay logs, deja marca en la maleta y sale sin tocar biblia/diario.
    - Integra LLM vía `scripts/llm.py` (OpenAI/Anthropic) y tiene fallback “stub”.
  - Cron configurado en `docker/cron_narrador`.

#### Fase 4 — Intenciones LLM + ejecución mecánica

- **Criterios**
  - ✅ Existe módulo de intenciones y decisor LLM.
  - ⏳ Métrica 20–30 llamadas/hora (pendiente de instrumentación/medición real).
- **Evidencia**
  - `scripts/intenciones.py` define `INTENCIONES_V0`.
  - `scripts/decisor_llm.py` pide JSON `{\"intencion\":\"nombre\"}` al LLM y mapea a teclas.
  - `scripts/agente_jugador.py` soporta `USE_LLM_INTENTIONS=1` y loguea `Decisión: Intención LLM: ...` si aplica.

#### Fase 5 — Operación + ganchos futuro

- **Criterios**
  - ✅ Guía mínima de operación en `README.md`.
  - ✅ Inbox por filesystem definido (sin bot).
  - ⏳ “Corre horas sin intervención” (pendiente de corrida prolongada estable).
- **Evidencia**
  - `README.md` incluye comandos `python3 -m scripts.*` y `docker compose up --build`.
  - `mundo/inbox/README.md` define propuesta de bandeja de entrada.

## Principios no negociables

- **Todo corre en Docker** y persiste por volúmenes. (ver [`docs/arquitectura.md`](arquitectura.md))
- **El filesystem es el bus de coordinación**: `mundo/` es la fuente de verdad.
- **Un solo writer por archivo**. Los logs del jugador son **append-only**.
- **El jugador no interpreta**: escribe crudo. La prosa la hace el narrador.

## Contrato del bus (`mundo/`)

```
mundo/
  logs/
    YYYY-MM-DD.md              ← Agente Jugador (append-only)
  maletas/
    maleta_001.md              ← Narrador (reescribe/append según diseño)
  biblia/
    personajes.md              ← Narrador
    fortaleza_actual.md        ← Narrador
  legends/
    mundo.md                   ← Agente Legends (futuro) / Narrador consulta
  diario.md                    ← Narrador
```

### Quién lee/escribe qué

- **Agente Jugador**
  - **Escribe**: `mundo/logs/YYYY-MM-DD.md` (append-only).
  - **Lee**: pantalla (tmux) y/o señales mínimas (DFHack).
  - **No toca**: `maletas/`, `biblia/`, `diario.md`.
- **Narrador (cron nocturno)**
  - **Lee**: `mundo/logs/`, `mundo/maletas/`, `mundo/biblia/`, `mundo/diario.md`.
  - **Escribe**: `mundo/maletas/`, `mundo/biblia/`, `mundo/diario.md`.
- **Legends (futuro)**
  - **Escribe**: `mundo/legends/mundo.md`.
  - **Lee**: exports/estado del mundo (vía DF/DFHack/Legends).

## Fase 0 — Arranque del repo y estructura

- **Objetivo**: dejar listo el esqueleto del proyecto + contrato de `mundo/`.
- **Entregables**:
  - Estructura de directorios: `mundo/`, `saves/`, `scripts/`, `docker/`.
  - `.env.example` (sin secretos).
  - `README.md` enlazando biblia/arquitectura/plan.
- **Criterios de salida**:
  - `mundo/` existe con placeholders (`diario.md`, `maletas/`, `biblia/`, `legends/`).
  - `.env.example` existe.
  - `docs/plan_fases.md` existe (este archivo).

## Fase 1 — Infraestructura Docker + DF + canal de logs

- **Objetivo**: levantar contenedor con DF + DFHack + Xvfb + tmux + Python + cron, y poder capturar pantalla/logs.
- **Entregables**:
  - `docker-compose.yml` + `docker/Dockerfile`.
  - Script mínimo de captura (tmux → snapshot).
- **Criterios de salida**:
  - `docker compose up` levanta el contenedor.
  - DF corre en una sesión tmux bajo Xvfb.
  - Se puede generar `mundo/logs/YYYY-MM-DD.md` con timestamps.
  - Los volúmenes persisten.

## Fase 2 — Agente Jugador v0 (script + logging estructurado)

- **Objetivo**: un agente mecánico que mueva a Gonzalo y loguee cada turno en formato parseable.
- **Formato de log por turno** (contrato):

```
## Turno HH:MM

**Pantalla:** <texto capturado>
**Contexto:** <estado mínimo>
**Decisión:** <intención simple>
**Teclas:** <secuencia enviada>
**Resultado:** <texto capturado después>
```

- **Entregables**:
  - `scripts/agente_jugador.py`
  - `scripts/tmux_io.py` (helper para leer/enviar a tmux, si aplica)
- **Criterios de salida**:
  - El agente corre en loop y mueve a Gonzalo.
  - El log diario es consistente, con timestamps y bloques completos.
  - Delays por contexto básicos (ver [`docs/timing_agente.md`](timing_agente.md)).

## Fase 3 — Narrador nocturno v0 (cron + crónica diaria mínima)

- **Objetivo**: procesar logs del día y producir crónica + updates de maleta/diario/biblia.
- **Entregables**:
  - `scripts/narrador_nocturno.py`
  - Config de cron en el contenedor.
- **Criterios de salida**:
  - Se puede ejecutar manualmente contra un log de prueba y produce:
    - Episodio 300–500 palabras con encabezado `Maleta N — Día N — Lugar`.
    - Updates coherentes de `mundo/maletas/` y `mundo/diario.md`.
  - Cron corre 1 vez por noche sin errores.

## Fase 4 — Refinamiento del jugador (intenciones LLM + ejecución mecánica)

- **Objetivo**: decisiones estratégicas con LLM (intenciones), ejecución determinista en script.
- **Entregables**:
  - Módulo “decisor” (LLM) → intención controlada.
  - Ajuste de consulta LLM solo en momentos “reales” (ver [`docs/timing_agente.md`](timing_agente.md)).
- **Criterios de salida**:
  - 20–30 llamadas al LLM por hora (aprox.).
  - Logs registran intención + ejecución.

## Fase 5 — Preparación de stream y ganchos futuros

- **Objetivo**: operación continua (horas) + documentación “onboarding” + hooks a futuro.
- **Entregables**:
  - Guía de operación (levantar contenedor + procesos) en `README.md`.
  - Diseño de “bandeja de entrada” por filesystem para mensajes de audiencia (sin implementar bots).
- **Criterios de salida**:
  - Sistema corre varias horas sin intervención frecuente.
  - Un tercero entiende el roadmap leyendo `README.md` + biblia + este plan.

## Futuro (no Fase 1)

- **Lava lamps enanas**: entropía desde frames ASCII (ver [`docs/ideas.md`](ideas.md)).
- **Overlay stream**: HUD periodístico con estado/fragmentos/log.
- **Bot interactivo**: Twitch/Telegram (cuando el stream base ya corra).
- **Podcast generado**: con revisión humana previa.
- **Crónica escrita larga**: series de ~10 capítulos.
