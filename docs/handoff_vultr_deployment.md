# Handoff — Deployment Vultr

## Contexto del proyecto

**Camino a la Ruina** es un stream 24/7 automatizado donde agentes IA juegan Dwarf
Fortress y un periodista gonzo llamado Gonzalo narra lo que ocurre.
Repo: https://github.com/abarza/Camino-Ruina

## Infraestructura

- VPS Vultr: Ubuntu 24.04, 2 vCPU, 4 GB RAM, Atlanta US, $20/mes
- Docker + Docker Compose instalados
- Repo clonado en `~/Camino-Ruina`
- DF 53.11 (Classic/SDL Linux) + DFHack 53.11-r2 en `~/Camino-Ruina/df/`
- Saves en `~/Camino-Ruina/saves/` (contiene `current/` y `region1/`)

## Arquitectura del contenedor

- Ubuntu 24.04 base
- Xvfb display virtual `:99`
- tmux sesión `df` corriendo DF/DFHack
- Python 3 venv + scripts en `/gonzalo/scripts/`
- Cron para narrador nocturno
- Volúmenes: `./mundo:/gonzalo/mundo`, `./saves:/df/data/save`, `./df:/opt/df`
- El agente se comunica con DFHack vía **`dfhack-run` CLI** (socket local), no TCP

## Diagnóstico de problemas anteriores

### Causa 1: `DF_CMD` apuntaba a `./dwarfort` (sin DFHack)

El default histórico era `DF_CMD=./dwarfort`, lo que lanzaba DF sin DFHack.
`dfhack-run` no puede conectar si DFHack no está inyectado.

**Fix aplicado:** `DF_CMD=./dfhack` en `.env.example` y `Dockerfile ENV`.

### Causa 2: AppArmor en Ubuntu 24.04 bloquea LD_PRELOAD de DFHack

Vultr corre AppArmor activo. `docker-compose.yml` ya tenía `seccomp:unconfined`
pero AppArmor puede bloquear `LD_PRELOAD` / `personality()` igualmente.

**Fix aplicado:** agregado `apparmor:unconfined` a `security_opt` en `docker-compose.yml`.

### Causa 3: Race condition — `dfhack-run` llamado antes de que DFHack inicialice

El entrypoint lanzaba DF y seguía inmediatamente. Si el agente corría antes de que
DFHack terminara de cargar, `dfhack-run` fallaba.

**Fix aplicado:** loop de espera en `entrypoint.sh` (max 60s, polling cada 2s).

## Cómo hacer el deploy (pasos en el VPS)

```bash
cd ~/Camino-Ruina
git pull

# Verificar que .env tiene DF_CMD=./dfhack
grep DF_CMD .env   # debe decir DF_CMD=./dfhack

docker compose down
docker compose up --build -d

# Verificar que DFHack respondió
docker logs $(docker ps -q) | grep -E "DFHack|listo"

# Verificar dfhack-run funciona
docker exec -it $(docker ps -q) /opt/df/dfhack-run lua "print('DFHack OK')"

# Correr el agente manualmente una vuelta
docker exec -it $(docker ps -q) python3 -m scripts.agente_jugador
```

## Verificación

1. `docker logs <container>` muestra `"DFHack listo."` (del wait loop)
2. `docker exec ... /opt/df/dfhack-run lua "print('ok')"` responde `ok`
3. `docker exec ... pgrep -a dwarfort` muestra dwarfort corriendo
4. `mundo/logs/<fecha>.md` contiene UNIT/POS/HP del aventurero tras correr el agente

## Si DFHack sigue sin funcionar

```bash
# Ver estado de AppArmor en el host (fuera del contenedor)
aa-status

# Nuclear option: privileged mode (último recurso)
# En docker-compose.yml, bajo el servicio camino:
#   privileged: true
# Esto da acceso completo al kernel — usar solo para diagnóstico.

# Ver qué bloquea desde el kernel
docker exec $(docker ps -q) dmesg | grep -i apparmor
```

## Comandos útiles para diagnóstico

```bash
# Procesos dentro del contenedor
docker exec $(docker ps -q) pgrep -a dwarfort
docker exec $(docker ps -q) pgrep -a dfhack

# Ver sesión tmux
docker exec $(docker ps -q) tmux capture-pane -t df:0.0 -p

# Logs del contenedor
docker logs $(docker ps -q) --tail 50

# Logs del agente
docker exec $(docker ps -q) tail -30 /gonzalo/mundo/logs/$(date +%Y-%m-%d).md
```
