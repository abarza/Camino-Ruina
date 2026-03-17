## Docker (Camino a la Ruina)

Este contenedor instala lo necesario para correr el sistema:

- Ubuntu 24.04
- Xvfb (DISPLAY virtual)
- tmux (sesión del juego / IO)
- Python 3 (scripts de agentes)
- cron (narrador nocturno)

### Dwarf Fortress / DFHack

Por licencias, **no se incluye** Dwarf Fortress dentro del repo. El contenedor asume que DF/DFHack están disponibles en `DF_DIR` (default: `/opt/df`).

Opciones:

- Montar un directorio `./df` en el host a `/opt/df` en el contenedor (ver `docker-compose.yml`).
- Cambiar `DF_DIR`/`DF_CMD` vía variables de entorno.
  - Default actual: `DF_CMD=./dwarfort` (modo classic estable en contenedor).
  - Para DFHack: `DF_CMD=./dfhack` (usa launcher de compatibilidad sin `setarch`, vía preload de `libdfhack.so`).

Si DF no está montado, el contenedor igual arranca y deja la sesión tmux lista.
