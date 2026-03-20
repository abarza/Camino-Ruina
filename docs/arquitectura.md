# Arquitectura — Camino a la Ruina

Todo vive dentro de un contenedor Docker. Nada en el host excepto volúmenes.

## Contenedor

- Ubuntu 24.04
- Dwarf Fortress 0.47.05 (text mode, ncurses) + DFHack 0.47.05-r8
- tmux (sesión `df` — DF corre aquí en terminal)
- Python 3 + scripts de agentes
- Cron para el narrador nocturno

## IO del agente (cómo interactúa con DF)

- **Lectura (estado estructurado)**: DFHack vía `dfhack-run` — consulta estado del juego como texto (unidad, posición, HP, NPCs cercanos, modo de juego).
- **Lectura (pantalla)**: `tmux capture-pane` — captura texto directo de la terminal donde corre DF.
- **Escritura (input)**: `tmux send-keys` — envía teclas a la sesión tmux donde corre DF.

## Volúmenes (persistentes, fuera de la imagen)

```yaml
volumes:
  - ./mundo:/gonzalo/mundo       # maletas, logs, biblia, diario
  - ./saves:/df/data/save        # saves de Dwarf Fortress
  - ./df:/opt/df                 # DF 0.47.05 + DFHack (binarios)
```

**Nota DF 0.47.x**: los saves van a `data/save/` directamente (no como 53.x que usaba `~/.local/share/`).

## Seguridad Docker

```yaml
security_opt:
  - seccomp:unconfined   # DFHack necesita setarch -R (deshabilitar ASLR)
  - apparmor:unconfined
```

## Secretos

```
.env          ← API keys reales (en .gitignore)
.env.example  ← estructura sin valores (en el repo)
```

## Portabilidad

Mover a otro PC = clonar repo + copiar volúmenes + `docker compose up`.

## Diagrama

```
┌──────────────────────────────────────────┐
│            Docker Container              │
│                                          │
│  tmux session "df"                       │
│      │                                   │
│      └──► Dwarf Fortress (TEXT mode)     │
│               + DFHack 0.47.05-r8        │
│                     │                    │
│         ┌───────────┴──────────┐         │
│    dfhack-run           tmux send-keys   │
│    (estado texto)       (input teclas)   │
│         │                    │           │
│    Agente Jugador ◄──────────┘           │
│         │                                │
│    Narrador (cron 20:30)                 │
│         │                                │
│         ▼                                │
│  ┌─────────────────────────┐             │
│  │       mundo/            │◄──── mount  │
│  │  logs/ maletas/ biblia/ │             │
│  └─────────────────────────┘             │
└──────────────────────────────────────────┘
```
