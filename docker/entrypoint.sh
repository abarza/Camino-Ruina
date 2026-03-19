#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
export TMUX_SESSION="${TMUX_SESSION:-df}"
export TMUX_PANE="${TMUX_PANE:-0}"
export DF_DIR="${DF_DIR:-/opt/df}"
export DF_CMD="${DF_CMD:-./dfhack}"

mkdir -p /gonzalo /gonzalo/mundo

# DF 53.x guarda en ~/.local/share/Bay 12 Games/Dwarf Fortress/save/
# Symlink al volumen montado para persistencia.
DF_SAVE_HOME="/root/.local/share/Bay 12 Games/Dwarf Fortress"
mkdir -p "${DF_SAVE_HOME}"
if [ ! -L "${DF_SAVE_HOME}/save" ]; then
  rm -rf "${DF_SAVE_HOME}/save"
  ln -s /df/data/save "${DF_SAVE_HOME}/save"
fi

if ! pgrep -x Xvfb >/dev/null 2>&1; then
  Xvfb "${DISPLAY}" -screen 0 1280x720x24 >/var/log/xvfb.log 2>&1 &
  sleep 1
fi

# Window manager (SDL2 necesita WM para recibir input via VNC).
if ! pgrep -x openbox >/dev/null 2>&1; then
  openbox >/dev/null 2>&1 &
fi

# VNC para setup inicial / debug visual.
if ! pgrep -x x11vnc >/dev/null 2>&1; then
  x11vnc -display "${DISPLAY}" -forever -nopw -listen 0.0.0.0 -rfbport 5900 \
    >/var/log/x11vnc.log 2>&1 &
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

echo "Camino a la Ruina listo. TMUX_SESSION=${TMUX_SESSION} DISPLAY=${DISPLAY} VNC=:5900"
exec bash
