#!/usr/bin/env bash
set -euo pipefail

export TMUX_SESSION="${TMUX_SESSION:-df}"
export TMUX_PANE="${TMUX_PANE:-0}"
export DF_DIR="${DF_DIR:-/opt/df}"
export DF_CMD="${DF_CMD:-./dfhack}"
export TERM="${TERM:-xterm-256color}"

mkdir -p /gonzalo /gonzalo/mundo

# Exportar variables de entorno para que cron las herede.
env >> /etc/environment

if ! tmux has-session -t "${TMUX_SESSION}" >/dev/null 2>&1; then
  tmux new-session -d -s "${TMUX_SESSION}" "bash"
fi

tmux send-keys -t "${TMUX_SESSION}:${TMUX_PANE}" "cd \"${DF_DIR}\" || true" C-m

if [ -d "${DF_DIR}" ]; then
  tmux send-keys -t "${TMUX_SESSION}:${TMUX_PANE}" "/usr/local/bin/launch_df.sh \"${DF_DIR}\" \"${DF_CMD}\"" C-m
else
  tmux send-keys -t "${TMUX_SESSION}:${TMUX_PANE}" "echo \"DF_DIR no existe (${DF_DIR}). Monta DF/DFHack en ${DF_DIR}.\" " C-m
fi

service cron start >/dev/null 2>&1 || true

# Esperar a que DFHack esté listo (max 60s), solo si DF_DIR existe y usamos dfhack.
if [ -d "${DF_DIR}" ] && [[ "${DF_CMD}" == *dfhack* ]]; then
  echo "Esperando DFHack..."
  for i in $(seq 1 30); do
    if "${DF_DIR}/dfhack-run" lua "print('ok')" 2>/dev/null | grep -q 'ok'; then
      echo "DFHack listo."
      break
    fi
    sleep 2
  done
fi

echo "Camino a la Ruina listo. TMUX_SESSION=${TMUX_SESSION} (text mode)"

# Lanzar agente jugador automáticamente si AGENT_AUTOSTART=1.
if [ "${AGENT_AUTOSTART:-0}" = "1" ]; then
  echo "Lanzando agente jugador en background..."
  cd /gonzalo
  python3 -m scripts.agente_jugador >> /var/log/agente.log 2>&1 &
  echo "Agente PID: $!"
fi

# Lanzar stream si STREAM_ENABLED=1.
if [ "${STREAM_ENABLED:-0}" = "1" ]; then
  echo "Lanzando stream en background..."
  /usr/local/bin/stream.sh &
  echo "Stream PID: $!"
fi

exec bash
