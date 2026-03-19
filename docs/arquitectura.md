# Arquitectura — Camino a la Ruina

Todo vive dentro de un contenedor Docker. Nada en el host excepto volúmenes.

## Contenedor

- Ubuntu 24.04
- Dwarf Fortress 53.11 Classic (SDL2) + DFHack 53.11-r2
- Xvfb (framebuffer virtual — DF renderiza en SDL2 aquí)
- openbox (window manager — SDL2 necesita WM para recibir input)
- x11vnc (VNC en puerto 5900 — para setup inicial y debug visual)
- ImageMagick + xdotool (captura de pantalla y envío de teclas)
- Python 3 + scripts de agentes
- Cron para el narrador nocturno

## IO del agente (cómo interactúa con DF)

- **Lectura**: DFHack vía `dfhack-run` — consulta estado del juego como texto estructurado (unidad, posición, HP, NPCs cercanos, modo de juego).
- **Escritura**: xdotool — envía teclas al display X11 donde DF corre en SDL2.
- **Screenshots**: ImageMagick `import -window root` — captura visual del framebuffer Xvfb.

## Volúmenes (persistentes, fuera de la imagen)

```yaml
volumes:
  - ./mundo:/gonzalo/mundo       # maletas, logs, biblia, diario
  - ./saves:/df/data/save        # saves de Dwarf Fortress
  - ./df:/opt/df                 # DF Classic + DFHack (binarios)
```

**Nota DF 53.x**: los saves van a `~/.local/share/Bay 12 Games/Dwarf Fortress/save/`. El entrypoint crea un symlink a `/df/data/save` (volumen montado) para persistencia.

## Seguridad Docker

```yaml
security_opt:
  - seccomp:unconfined   # DFHack necesita setarch -R (deshabilitar ASLR)
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
│  Xvfb :99 ──► openbox (WM)              │
│      │                                   │
│      ├──► Dwarf Fortress (SDL2)          │
│      │        + DFHack 53.11-r2          │
│      │              │                    │
│      └──► x11vnc (:5900)                 │
│                     │                    │
│         ┌───────────┴──────────┐         │
│    dfhack-run              xdotool       │
│    (estado texto)          (teclas)       │
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
