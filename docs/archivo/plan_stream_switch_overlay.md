# Plan: Switch On/Off para Stream + Overlay de día/ubicación

## Contexto

El stream de YouTube funciona 24/7 pero los lives de YouTube no pueden ser eternos (YouTube los corta después de ~12h o al perder conexión). Necesitamos:
1. Un **switch para prender/apagar** el stream sin reiniciar el container
2. Un **overlay en pantalla** mostrando el día y la ubicación actual de Gonzalo

## Estado actual

- `docker/stream.sh` corre en un loop watchdog infinito (si ffmpeg muere, lo reinicia)
- Se lanza desde `entrypoint.sh` si `STREAM_ENABLED=1` — pero no hay forma de pararlo/prenderlo sin reiniciar el container
- No hay overlay en el stream, solo la terminal raw de DF
- `dfhack_state.lua` ya extrae SITE y REGION del juego (la data para el overlay ya existe)

## Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `docker/stream.sh` | Refactorizar watchdog: escucha archivo de señal + agregar filtro drawtext |
| `docker/entrypoint.sh` | Orquestar overlay daemon + stream watchdog |
| `scripts/stream_overlay.py` | **Nuevo** — daemon que consulta DFHack cada 30s y escribe overlay text |
| `docker/stream_control.sh` | **Nuevo** — CLI: `stream_control.sh start|stop|status` |

## Implementación

### 1. `docker/stream_control.sh` — Switch on/off

Usa un archivo de señal `/tmp/stream.enabled`:
- `start`: crea el archivo, stream.sh detecta y arranca ffmpeg
- `stop`: borra el archivo, stream.sh detecta y mata ffmpeg
- `status`: reporta si está corriendo

```bash
docker compose exec camino stream_control.sh start
docker compose exec camino stream_control.sh stop
docker compose exec camino stream_control.sh status
```

### 2. `docker/stream.sh` — Watchdog con señal

El loop revisa `/tmp/stream.enabled` antes de cada ciclo:
- Archivo existe → arrancar/mantener ffmpeg
- Archivo no existe → matar ffmpeg/xterm, esperar

### 3. `scripts/stream_overlay.py` — Generador de overlay

Daemon que cada 30s:
- Consulta `dfhack_io.get_game_state()`
- Extrae SITE/REGION
- Escribe a `/tmp/stream_overlay.txt`: `Día 3 — The Hills of Thundering`

### 4. ffmpeg `drawtext` — Overlay en el stream

```
-vf "drawtext=textfile=/tmp/stream_overlay.txt:reload=1:fontsize=16:fontcolor=white:borderw=2:bordercolor=black:x=10:y=h-th-10"
```

### 5. `docker/entrypoint.sh` — Orquestar

- Lanzar `stream_overlay.py` en background (siempre)
- Lanzar `stream.sh` en background (watchdog siempre corre)
- Si `STREAM_ENABLED=1` → crear `/tmp/stream.enabled` (autostart)

## Flujo

```
entrypoint.sh
  ├─ Lanzar stream_overlay.py (cada 30s → /tmp/stream_overlay.txt)
  ├─ Lanzar stream.sh (watchdog, espera /tmp/stream.enabled)
  └─ Si STREAM_ENABLED=1 → touch /tmp/stream.enabled

Prender:  docker compose exec camino stream_control.sh start
Apagar:   docker compose exec camino stream_control.sh stop
Estado:   docker compose exec camino stream_control.sh status
```

## Verificación

1. `stream_control.sh status` reporta estado correcto
2. `start` → stream aparece en YouTube con overlay
3. `stop` → stream se detiene
4. `start` de nuevo → vuelve sin reiniciar container
5. Overlay muestra día y ubicación cada ~30s
6. Agente jugador y narrador no se ven afectados
