#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
export TMUX_SESSION="${TMUX_SESSION:-df}"
export TMUX_PANE="${TMUX_PANE:-0}"
export DF_DIR="${DF_DIR:-/opt/df}"
export DF_CMD="${DF_CMD:-./dwarfort}"

mkdir -p /gonzalo /gonzalo/mundo

if ! pgrep -x Xvfb >/dev/null 2>&1; then
  Xvfb "${DISPLAY}" -screen 0 1280x720x24 >/var/log/xvfb.log 2>&1 &
fi

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

echo "Camino a la Ruina listo. TMUX_SESSION=${TMUX_SESSION} DISPLAY=${DISPLAY}"
exec bash
