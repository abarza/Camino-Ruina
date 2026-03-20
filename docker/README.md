## Docker (Camino a la Ruina)

Este contenedor instala lo necesario para correr el sistema:

- Ubuntu 24.04
- tmux (sesión del juego / IO)
- ncurses (DF 0.47 text mode)
- SDL 1.2 + audio libs (DF 0.47 las linkea internamente)
- Python 3 (scripts de agentes)
- cron (narrador nocturno)

### Dwarf Fortress / DFHack

Por licencias, **no se incluye** Dwarf Fortress dentro del repo. El contenedor asume que DF/DFHack están disponibles en `DF_DIR` (default: `/opt/df`).

Opciones:

- Montar un directorio `./df` en el host a `/opt/df` en el contenedor (ver `docker-compose.yml`).
- Cambiar `DF_DIR`/`DF_CMD` vía variables de entorno.
  - Default: `DF_CMD=./dfhack` (DF 0.47.05 con DFHack 0.47.05-r8, text mode).

Si DF no está montado, el contenedor igual arranca y deja la sesión tmux lista.

### Text mode

DF 0.47.05 corre con `PRINT_MODE:TEXT` (ncurses puro). No necesita display gráfico.
El agente interactúa via `tmux send-keys` (input) y `tmux capture-pane` (lectura).
