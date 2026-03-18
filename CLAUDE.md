# CLAUDE.md — Camino a la Ruina

## Project Overview

**Camino a la Ruina** is a 24/7 automated Dwarf Fortress Adventure Mode streaming project. An AI-controlled character named Gonzalo (a gonzo journalist) explores a procedurally generated world, with autonomous narrative generation and multi-output content streams.

Three content outputs:
1. **24/7 live stream** — raw gameplay
2. **Narrative episodes** — daily AI-written chronicles (narrador nocturno)
3. **Long-form written series / podcasts** — future phases

Central question: *"Why do people build things they know will be lost?"*

## Repository Structure

```
Camino-Ruina/
├── scripts/           # Python agent implementations (~560 LOC)
│   ├── agente_jugador.py    # Main game loop agent
│   ├── narrador_nocturno.py # Nightly narrative generator (cron 03:30)
│   ├── captura_pantalla.py  # Screen capture utility
│   ├── tmux_io.py           # tmux interface & ANSI sanitization
│   ├── llm.py               # LLM abstraction (OpenAI / Anthropic)
│   ├── decisor_llm.py       # Strategic decision maker via LLM
│   └── intenciones.py       # Intention definitions (dataclasses)
├── docker/            # Container config (Dockerfile, entrypoint, launcher)
├── docs/              # Project documentation (Spanish)
│   ├── gonzalo_biblia_v3.md # Character bible & narrative tone guide
│   ├── plan_fases.md        # Phased roadmap
│   ├── arquitectura.md      # Architecture diagram
│   └── ...
├── mundo/             # Persistent filesystem bus (single source of truth)
│   ├── logs/          # Daily agent logs (append-only, YYYY-MM-DD.md)
│   ├── maletas/       # Narrative artifacts ("suitcases")
│   ├── biblia/        # Character DB & fortress state
│   ├── diario.md      # Gonzalo's journal
│   ├── legends/       # World history exports (future)
│   └── inbox/         # External message hook (future)
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Tech Stack

- **Language**: Python 3 (all agents and utilities)
- **Shell**: Bash (Docker entrypoint, DF launcher)
- **Container**: Docker + Docker Compose (Ubuntu 24.04 base)
- **Display**: Xvfb (virtual framebuffer at :99)
- **Terminal**: tmux (game session multiplexing)
- **Scheduling**: cron (nightly narrator at 03:30)
- **LLM Providers**: OpenAI (`gpt-4o-mini`) or Anthropic (`claude-3-5-sonnet-latest`), toggled via `LLM_PROVIDER` env var

## Dependencies

Defined in `requirements.txt`:
```
python-dotenv>=1.0.1
openai>=1.40.0
anthropic>=0.34.0
```

System deps are installed via the Dockerfile (SDL2 libs, Xvfb, tmux, cron, Python 3 venv).

## Running Scripts

All Python scripts are invoked as modules from the project root:

```bash
python3 -m scripts.agente_jugador       # Start the player agent loop
python3 -m scripts.narrador_nocturno     # Run the nightly narrator
python3 -m scripts.captura_pantalla      # Capture current screen
```

For Docker:
```bash
docker compose build
docker compose up
```

## Environment Configuration

Copy `.env.example` to `.env` and fill in API keys. Key variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `LLM_PROVIDER` | `openai` or `anthropic` | `openai` |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `OPENAI_MODEL` | OpenAI model | `gpt-4o-mini` |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `ANTHROPIC_MODEL` | Anthropic model | `claude-3-5-sonnet-latest` |
| `MUNDO_DIR` | Path to mundo/ state dir | `/gonzalo/mundo` |
| `DF_DIR` | Dwarf Fortress install path | `/opt/df` |
| `DF_CMD` | DF executable command | `./dwarfort` |

## Architecture & Key Patterns

### Filesystem as Message Bus
The `mundo/` directory is the **single source of truth**. Agents communicate exclusively through file read/write contracts — no queues, no sockets. Critical rule: **one writer per file; logs are append-only**.

### Layered Decision-Making
- **Level 1 (Strategic)**: LLM decides *intentions* (e.g., "go north", "talk to NPC") — see `decisor_llm.py`
- **Level 2 (Mechanical)**: Scripts execute deterministic key sequences via tmux — see `intenciones.py`
- This keeps LLM calls to ~20-30/hour

### Agent Separation
Each agent has a single responsibility:
- **agente_jugador**: Reads screen → decides action → sends keys → logs state
- **narrador_nocturno**: Reads daily logs → generates narrative prose → updates mundo/ files
- Future agents (Legends parser, Bot, Producer) follow the same pattern

### Log Format Contract (Turn Structure)
```markdown
## Turno HH:MM

**Pantalla:** [raw screen text]
**Contexto:** [exploración | combate | conversación | inventario]
**Decisión:** [agent choice]
**Teclas:** [keys sent]
**Resultado:** [screen after action]
```

## Code Conventions

- **Language**: Python code uses English for stdlib/library calls; **all docstrings, comments, variable names, and documentation are in Spanish**
- **Type hints**: Used throughout (`from __future__ import annotations`)
- **Data structures**: Frozen dataclasses for immutable state (`Turno`, `TmuxTarget`, `LlmConfig`, `Intencion`, `EstadoMinimo`)
- **Path handling**: Always use `pathlib.Path`
- **Naming**: `snake_case` for files and functions; `SCREAMING_SNAKE_CASE` for env vars
- **Entry points**: Scripts use `if __name__ == "__main__": raise SystemExit(main())` pattern
- **Imports**: Lazy imports for heavy dependencies (e.g., `openai`, `anthropic` imported inside functions)

## Testing

No formal test framework is configured yet. Validate with:

```bash
# Syntax check all Python files
python3 -m py_compile scripts/agente_jugador.py
python3 -m py_compile scripts/narrador_nocturno.py
# ... etc.

# Validate Docker Compose config
docker compose config
```

## Linting & Formatting

No linting tools are configured (no flake8, black, pylint, or pyproject.toml). Code follows PEP 8 conventions implicitly.

## Git Practices

- `.env` is gitignored (secrets)
- `__pycache__/`, `.mypy_cache/`, `.pytest_cache/` are gitignored
- Heavy directories excluded: `df/`, `saves/` (local game binaries/saves)
- `mundo/` content is tracked (it's the persistent state bus)

## Key Files for Understanding the System

| File | Why it matters |
|------|---------------|
| `scripts/agente_jugador.py` | Core game loop — the heart of the agent |
| `scripts/llm.py` | LLM abstraction layer — how AI calls are made |
| `scripts/tmux_io.py` | All game I/O flows through here |
| `scripts/intenciones.py` | Defines the vocabulary of possible actions |
| `docs/gonzalo_biblia_v3.md` | Character bible — essential for narrative tone |
| `docs/plan_fases.md` | Project roadmap and phase definitions |
| `docs/arquitectura.md` | System architecture diagram |
| `mundo/logs/` | Daily truth — what actually happened in-game |

## Common Tasks

**Add a new intention/action**: Define a new `Intencion` in `scripts/intenciones.py` with name, description, key sequence, and suggested context.

**Add a new agent**: Create a new file in `scripts/`, follow the existing pattern (frozen dataclasses, `main()` entry point, read/write to `mundo/`). Register it in cron or entrypoint as needed.

**Change LLM provider**: Update `LLM_PROVIDER` in `.env`. Both OpenAI and Anthropic are supported via `scripts/llm.py`.

**Read game state**: Agent state flows through `mundo/logs/YYYY-MM-DD.md` files. The narrator reads these to generate narrative content.
