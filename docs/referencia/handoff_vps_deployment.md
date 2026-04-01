# Handoff — Deployment VPS (Hetzner)

## Contexto del proyecto

**Camino a la Ruina** es un stream 24/7 automatizado donde agentes IA juegan Dwarf
Fortress y un periodista gonzo llamado Gonzalo narra lo que ocurre.
Repo: https://github.com/abarza/Camino-Ruina

## Infraestructura

- VPS Hetzner CX23: Ubuntu 24.04, 2 vCPU, 4 GB RAM, 40 GB SSD, Helsinki, $3.49/mes
- IP: `135.181.148.23`
- Docker + Docker Compose instalados
- Repo clonado en `~/camino-a-la-ruina`
- DF 0.47.05 (text mode) + DFHack 0.47.05-r8 en `~/camino-a-la-ruina/df/`
- Saves en `~/camino-a-la-ruina/saves/`

## Arquitectura del contenedor

- Ubuntu 24.04 base
- tmux sesión `df` corriendo DF en text mode (ncurses)
- Python 3 venv + scripts en `/gonzalo/scripts/`
- Cron para narrador nocturno
- Volúmenes: `./mundo:/gonzalo/mundo`, `./saves:/df/data/save`, `./df:/opt/df`
- El agente se comunica con DFHack vía **`dfhack-run` CLI** (socket local)
- Input via `tmux send-keys`, lectura via `tmux capture-pane`
- **Sin Xvfb, VNC, SDL2, xdotool** — todo es terminal pura

## Cómo hacer el deploy (pasos en el VPS)

```bash
cd ~/camino-a-la-ruina
git pull

# Verificar que .env tiene DF_CMD=./dfhack
grep DF_CMD .env   # debe decir DF_CMD=./dfhack

docker compose down
docker compose up --build -d

# Verificar que DFHack respondió
docker logs $(docker ps -q) | grep -E "DFHack|listo"

# Verificar dfhack-run funciona
docker exec $(docker ps -q) /opt/df/dfhack-run lua "print('DFHack OK')"

# Ver pantalla de DF
docker exec $(docker ps -q) tmux capture-pane -t df:0 -p

# Setup inicial (si no hay save): attachar a tmux y crear mundo/aventurero
docker exec -it $(docker ps -q) tmux attach -t df
# Ctrl+B, D para salir de tmux sin cerrarlo

# Correr el agente manualmente (si AGENT_AUTOSTART=0)
docker exec $(docker ps -q) python3 -m scripts.agente_jugador

# O prender AGENT_AUTOSTART=1 en .env para que arranque solo con el container
```

## Verificación

1. `docker logs <container>` muestra `"DFHack listo."` (del wait loop)
2. `docker exec ... /opt/df/dfhack-run lua "print('ok')"` responde `ok`
3. `docker exec ... pgrep -a Dwarf_Fortress` muestra DF corriendo
4. `mundo/logs/<fecha>.md` contiene UNIT/POS/HP del aventurero tras correr el agente
5. **No debe haber** procesos Xvfb, x11vnc, openbox

## Comandos útiles para diagnóstico

```bash
# Procesos dentro del contenedor
docker exec $(docker ps -q) pgrep -a Dwarf_Fortress

# Ver sesión tmux (pantalla de DF)
docker exec $(docker ps -q) tmux capture-pane -t df:0 -p

# Estado del aventurero via DFHack
docker exec $(docker ps -q) /opt/df/dfhack-run lua "dofile('/gonzalo/scripts/dfhack_state.lua')"

# Logs del contenedor
docker logs $(docker ps -q) --tail 50

# Logs del agente
docker exec $(docker ps -q) tail -30 /gonzalo/mundo/logs/$(date +%Y-%m-%d).md
```
