# Arquitectura — Camino a la Ruina

Todo vive dentro de un contenedor Docker. Nada en el host excepto volúmenes.

## Contenedor

- Ubuntu 24.04
- Dwarf Fortress (Steam/Classic) + DFHack
- Xvfb (framebuffer virtual — DF necesita "pantalla" pero nadie la mira)
- tmux (sesión del juego, los agentes leen/escriben vía tmux)
- Python 3 + scripts de agentes
- Cron para el narrador nocturno

## Volúmenes (persistentes, fuera de la imagen)

```yaml
volumes:
  - ./mundo:/gonzalo/mundo       # maletas, logs, biblia, diario
  - ./saves:/df/data/save        # saves de Dwarf Fortress
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
┌─────────────────────────────────────┐
│           Docker Container          │
│                                     │
│  Xvfb ──► Dwarf Fortress + DFHack  │
│                  │                  │
│               tmux                  │
│              ┌───┴───┐              │
│         Agente      Agente          │
│        Jugador     Narrador         │
│           │           │             │
│           ▼           ▼             │
│  ┌─────────────────────────┐        │
│  │       mundo/            │◄──mount│
│  │  logs/ maletas/ biblia/ │        │
│  └─────────────────────────┘        │
└─────────────────────────────────────┘
```
