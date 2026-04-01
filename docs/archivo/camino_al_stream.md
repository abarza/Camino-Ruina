# Plan: Camino al Stream — Terminal DF → YouTube Live

## Context

Gonzalo Usuknol corre 24/7 en un VPS Hetzner (Helsinki). DF 0.47.05 en text mode,
agente jugador activo, narrador nocturno via cron. Todo funciona en terminal pura
dentro de Docker (tmux session `df`).

El objetivo es transmitir esa terminal como stream 24/7 a Twitch y YouTube
simultáneamente. Según la biblia (§2): "OpenClaw juega. El mundo vive. La audiencia
observa. No necesita narración elaborada — solo que pase algo."

**Lo que se ve**: la terminal de DF tal cual — ncurses, ASCII, el mapa, Gonzalo
moviéndose, NPCs, combate, todo en texto.

**Audio**: opcional — música de fondo ambient/lo-fi si es simple de implementar.
Si no, sin audio por ahora.

**Plataforma**: YouTube Live (un solo destino, un solo ffmpeg).

## Enfoque técnico

DF corre en tmux dentro de Docker. Para streamear necesitamos capturar esa terminal
como video y empujar via RTMP. El approach:

1. Xvfb crea un display virtual pequeño (solo para renderizar la terminal)
2. xterm se conecta al tmux session `df` y muestra DF en ese display
3. ffmpeg captura el display via x11grab y encodea a H.264
4. ffmpeg empuja el stream a Twitch y YouTube via RTMP

Xvfb aquí es solo para el stream — DF sigue corriendo en text mode puro, el input
sigue siendo tmux send-keys. No hay conflicto con la arquitectura actual.

---

## Fases

### Fase 0: Stream básico a YouTube Live

**Archivos a modificar:**

#### `docker/Dockerfile`
- Agregar paquetes: `xvfb`, `xterm`, `ffmpeg`
- No agregar SDL2/openbox/x11vnc — solo lo mínimo para captura

#### `docker/entrypoint.sh`
- Agregar bloque condicional `STREAM_ENABLED=1`:
  - Levantar Xvfb en un display secundario (`:1`, no `:99`)
  - Lanzar xterm conectado a `tmux attach -t df` en ese display
  - Lanzar ffmpeg capturando el display y empujando a RTMP

#### `.env.example`
- Agregar: `STREAM_ENABLED=0`, `STREAM_KEY=`, `STREAM_URL=rtmp://a.rtmp.youtube.com/live2`

#### Nuevo: `docker/stream.sh`
- Script que configura Xvfb + xterm + ffmpeg
- Parámetros: resolución, FPS, bitrate, RTMP URL + key
- Corre en background, se reinicia si ffmpeg muere

**Criterio de éxito:**
- Stream visible en YouTube mostrando la terminal de DF
- DF sigue corriendo normalmente (agente no se ve afectado)
- El stream se ve legible (font size, contraste, resolución correcta)

**Test:**
```bash
# En el VPS:
docker compose exec camino pgrep -a ffmpeg    # ffmpeg corriendo
docker compose exec camino pgrep -a xterm     # xterm corriendo
docker compose exec camino pgrep -a Xvfb      # Xvfb corriendo
# Verificar en YouTube que se ve la terminal de DF
# Verificar que el agente sigue corriendo:
docker compose exec camino pgrep -a python3
```

---

### Fase 1: Música de fondo (opcional)

**Acciones:**
- Conseguir loop ambient/lo-fi royalty-free (1-2 archivos .mp3/.ogg)
- ffmpeg mezcla audio con el video capturado (`-i music.mp3 -stream_loop -1`)
- Volumen bajo — la música es fondo, no protagonista

**Archivos a modificar:**
- `docker/stream.sh` — agregar input de audio a ffmpeg
- Nuevo: `docker/music/` — directorio con archivos de audio

**Criterio de éxito:**
- Stream tiene música de fondo suave
- La música loopea sin cortes audibles
- Se puede desactivar con variable de entorno

**Test:**
- Escuchar el stream — música presente y no invasiva

---

### Fase 2: Estabilidad y auto-recovery ✅ (2026-03-20)

- [x] Watchdog loop en `stream.sh`: si ffmpeg muere, revisa Xvfb/xterm y reinicia en 10s
- [x] Logging a `/var/log/stream.log` con timestamps
- [x] Funciones separadas `start_xvfb`, `start_xterm`, `run_ffmpeg` para recovery granular

**Test:**
```bash
# Matar ffmpeg y verificar que se reinicia:
docker compose exec camino kill $(pgrep ffmpeg)
sleep 30
docker compose exec camino pgrep -a ffmpeg    # debe estar corriendo de nuevo
```

---

## Archivos modificados (resumen)

| Archivo | Acción |
|---|---|
| `docker/Dockerfile` | Agregar xvfb, xterm, ffmpeg |
| `docker/entrypoint.sh` | Bloque condicional STREAM_ENABLED |
| `docker/stream.sh` | Nuevo — orquesta Xvfb + xterm + ffmpeg |
| `docker/music/` | Nuevo (Fase 2) — archivos de audio |
| `.env.example` | STREAM_ENABLED, STREAM_KEY, STREAM_URL |
| `docker-compose.yml` | Sin cambios (no se exponen puertos) |

## Archivos sin cambios

Todo lo de scripts/, mundo/, df/ — el stream es ortogonal al agente.

## Decisiones

1. **Resolución**: 1280x720 (720p) — legible, bajo CPU
2. **FPS**: 15fps — suficiente para texto
3. **Font**: Fira Code (preferida) o Terminus (fallback)
4. **Destino**: YouTube Live (un solo ffmpeg, sin dual stream por ahora)

## Verificación end-to-end

1. DF corre en text mode dentro de tmux
2. Agente jugador mueve a Gonzalo y escribe logs
3. Xvfb renderiza xterm conectado a tmux
4. ffmpeg captura y empuja a YouTube Live
5. Stream visible en YouTube con terminal legible
6. Narrador nocturno sigue corriendo via cron
7. Todo sobrevive 24h sin intervención manual
